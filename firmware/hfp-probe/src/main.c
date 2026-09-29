#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "driver/i2s_std.h"
#include "boot_hid.h"
#include "hfp_reconnect.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_bt_api.h"
#include "esp_hf_client_api.h"
#include "esp_hf_client_legacy_api.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "nvs.h"

#define MIC_RATE 16000
#define READ_SAMPLES 128
#define AUDIO_RING_SAMPLES 8192

static const char *TAG = "VOICE_PUCK";
static int32_t mic_samples[READ_SAMPLES];
static int16_t audio_ring[AUDIO_RING_SAMPLES];
static size_t ring_read;
static size_t ring_write;
static size_t ring_count;
static portMUX_TYPE ring_lock = portMUX_INITIALIZER_UNLOCKED;
static esp_bd_addr_t peer_address;
static volatile bool audio_connected;
static volatile bool wideband;
static volatile bool service_connected;
static hfp_reconnect_t reconnect;
static nvs_handle_t peer_store;
static portMUX_TYPE reconnect_lock = portMUX_INITIALIZER_UNLOCKED;

static uint32_t now_ms(void)
{
    return (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
}

static void reconnect_task(void *arg)
{
    (void)arg;
    while (true) {
        portENTER_CRITICAL(&reconnect_lock);
        bool attempt = hfp_reconnect_poll(&reconnect, now_ms());
        esp_bd_addr_t target;
        memcpy(target, reconnect.peer, sizeof(target));
        portEXIT_CRITICAL(&reconnect_lock);
        if (attempt) {
            esp_err_t err = esp_hf_client_connect(target);
            ESP_LOGI(TAG, "auto-connect HFP to previous host: %s", esp_err_to_name(err));
            if (err != ESP_OK) {
                portENTER_CRITICAL(&reconnect_lock);
                hfp_reconnect_disconnected(&reconnect, now_ms());
                portEXIT_CRITICAL(&reconnect_lock);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}

static void ring_reset(void)
{
    portENTER_CRITICAL(&ring_lock);
    ring_read = ring_write = ring_count = 0;
    portEXIT_CRITICAL(&ring_lock);
}

static void ring_push(int16_t value)
{
    portENTER_CRITICAL(&ring_lock);
    if (ring_count == AUDIO_RING_SAMPLES) {
        ring_read = (ring_read + 1) % AUDIO_RING_SAMPLES;
        --ring_count;
    }
    audio_ring[ring_write] = value;
    ring_write = (ring_write + 1) % AUDIO_RING_SAMPLES;
    ++ring_count;
    portEXIT_CRITICAL(&ring_lock);
}

static uint32_t outgoing_audio(uint8_t *buffer, uint32_t length)
{
    if (!audio_connected || length % sizeof(int16_t) != 0) {
        return 0;
    }
    size_t wanted = length / sizeof(int16_t);
    portENTER_CRITICAL(&ring_lock);
    if (ring_count < wanted) {
        portEXIT_CRITICAL(&ring_lock);
        return 0;
    }
    for (size_t i = 0; i < wanted; ++i) {
        int16_t value = audio_ring[ring_read];
        ring_read = (ring_read + 1) % AUDIO_RING_SAMPLES;
        memcpy(buffer + i * sizeof(value), &value, sizeof(value));
    }
    ring_count -= wanted;
    portEXIT_CRITICAL(&ring_lock);
    return length;
}

static void incoming_audio(const uint8_t *buffer, uint32_t length)
{
    (void)buffer;
    (void)length;
    // V1 prototype has no speaker. Mac playback remains on its selected output.
}

static void hf_callback(esp_hf_client_cb_event_t event, esp_hf_client_cb_param_t *param)
{
    switch (event) {
    case ESP_HF_CLIENT_CONNECTION_STATE_EVT:
        ESP_LOGI(TAG, "HFP connection state=%d", param->conn_stat.state);
        portENTER_CRITICAL(&reconnect_lock);
        if (param->conn_stat.state == ESP_HF_CLIENT_CONNECTION_STATE_DISCONNECTED) {
            hfp_reconnect_disconnected(&reconnect, now_ms());
        } else {
            // Includes inbound RFCOMM setup; wait for completion before retrying.
            reconnect.busy = true;
        }
        portEXIT_CRITICAL(&reconnect_lock);
        if (param->conn_stat.state == ESP_HF_CLIENT_CONNECTION_STATE_SLC_CONNECTED) {
            memcpy(peer_address, param->conn_stat.remote_bda, ESP_BD_ADDR_LEN);
            service_connected = true;
            portENTER_CRITICAL(&reconnect_lock);
            bool changed = hfp_reconnect_remember(&reconnect, peer_address);
            portEXIT_CRITICAL(&reconnect_lock);
            if (changed) {
                esp_err_t saved = nvs_set_blob(peer_store, "last_peer", peer_address, sizeof(peer_address));
                if (saved == ESP_OK) saved = nvs_commit(peer_store);
                ESP_LOGI(TAG, "save last connected host: %s", esp_err_to_name(saved));
            }
            boot_hid_set_hfp_connected(true, peer_address);
            esp_err_t err = esp_hf_client_connect_audio(peer_address);
            ESP_LOGI(TAG, "request SCO audio: %s", esp_err_to_name(err));
        } else if (param->conn_stat.state == ESP_HF_CLIENT_CONNECTION_STATE_DISCONNECTED) {
            service_connected = false;
            boot_hid_set_hfp_connected(false, NULL);
            audio_connected = false;
            ring_reset();
        }
        break;
    case ESP_HF_CLIENT_AUDIO_STATE_EVT:
        ESP_LOGI(TAG, "SCO audio state=%d", param->audio_stat.state);
        if (param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_CONNECTED ||
            param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_CONNECTED_MSBC) {
            wideband = param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_CONNECTED_MSBC;
            ring_reset();
            ESP_ERROR_CHECK(esp_hf_client_register_data_callback(incoming_audio, outgoing_audio));
            audio_connected = true;
            ESP_LOGI(TAG, "audio ready: %s", wideband ? "mSBC 16 kHz" : "CVSD 8 kHz");
        } else if (param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_DISCONNECTED) {
            audio_connected = false;
            ring_reset();
        }
        break;
    case ESP_HF_CLIENT_PROF_STATE_EVT:
        ESP_LOGI(TAG, "HFP profile state=%d", param->prof_stat.state);
        if (param->prof_stat.state == ESP_HF_INIT_SUCCESS) {
            portENTER_CRITICAL(&reconnect_lock);
            reconnect.ready = true;
            portEXIT_CRITICAL(&reconnect_lock);
        }
        break;
    default:
        break;
    }
}

static void gap_callback(esp_bt_gap_cb_event_t event, esp_bt_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_BT_GAP_CFM_REQ_EVT:
        ESP_LOGI(TAG, "SSP confirmation requested");
        esp_bt_gap_ssp_confirm_reply(param->cfm_req.bda, true);
        break;
    case ESP_BT_GAP_PIN_REQ_EVT: {
        esp_bt_pin_code_t pin = {'0', '0', '0', '0'};
        esp_bt_gap_pin_reply(param->pin_req.bda, true, 4, pin);
        break;
    }
    case ESP_BT_GAP_AUTH_CMPL_EVT:
        ESP_LOGI(TAG, "pairing %s", param->auth_cmpl.stat == ESP_BT_STATUS_SUCCESS ? "succeeded" : "failed");
        break;
    default:
        break;
    }
}

static void mic_task(void *arg)
{
    (void)arg;
    i2s_chan_handle_t rx = NULL;
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&channel, NULL, &rx));

    i2s_std_config_t config = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(MIC_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = GPIO_NUM_26,
            .ws = GPIO_NUM_25,
            .dout = I2S_GPIO_UNUSED,
            .din = GPIO_NUM_33,
        },
    };
    config.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx, &config));
    ESP_ERROR_CHECK(i2s_channel_enable(rx));
    ESP_LOGI(TAG, "INMP441 ready: D26=SCK D25=WS D33=SD, 16 kHz");

    uint32_t blocks = 0;
    while (true) {
        size_t bytes_read = 0;
        if (i2s_channel_read(rx, mic_samples, sizeof(mic_samples), &bytes_read, 1000) != ESP_OK) {
            continue;
        }
        int64_t sum_abs = 0;
        size_t count = bytes_read / sizeof(mic_samples[0]);
        for (size_t i = 0; i < count; ++i) {
            int32_t sample = mic_samples[i] >> 16;
            sum_abs += sample < 0 ? -sample : sample;
            if (audio_connected && (wideband || i % 2 == 0)) {
                ring_push((int16_t)sample);
            }
        }
        if (audio_connected) {
            esp_hf_client_outgoing_data_ready();
        }
        if (++blocks % 125 == 0 && count > 0) {
            ESP_LOGI(TAG, "mic mean_abs=%ld, HFP=%d, SCO=%d, codec=%s",
                     (long)(sum_abs / count), service_connected, audio_connected,
                     wideband ? "mSBC" : "CVSD");
        }
    }
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    ESP_ERROR_CHECK(nvs_open("voxu", NVS_READWRITE, &peer_store));
    esp_bd_addr_t saved_peer;
    size_t saved_size = sizeof(saved_peer);
    err = nvs_get_blob(peer_store, "last_peer", saved_peer, &saved_size);
    if (err == ESP_OK && saved_size == sizeof(saved_peer)) {
        hfp_reconnect_remember(&reconnect, saved_peer);
        ESP_LOGI(TAG, "loaded previous host from NVS");
    } else {
        ESP_LOGI(TAG, "no previous host; pair/connect from the computer once");
    }
    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_BLE));
    esp_bt_controller_config_t bt_config = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bt_controller_init(&bt_config));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_CLASSIC_BT));
    esp_bluedroid_config_t blue_config = BT_BLUEDROID_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bluedroid_init_with_cfg(&blue_config));
    ESP_ERROR_CHECK(esp_bluedroid_enable());

    ESP_ERROR_CHECK(esp_bt_gap_register_callback(gap_callback));
    ESP_ERROR_CHECK(esp_hf_client_register_callback(hf_callback));
    boot_hid_init();
    ESP_ERROR_CHECK(esp_hf_client_init());
    ESP_ERROR_CHECK(esp_bt_gap_set_device_name("Voice Puck V1"));
    esp_bt_io_cap_t io_capability = ESP_BT_IO_CAP_NONE;
    ESP_ERROR_CHECK(esp_bt_gap_set_security_param(ESP_BT_SP_IOCAP_MODE, &io_capability,
                                                  sizeof(io_capability)));
    esp_bt_pin_code_t pin = {'0', '0', '0', '0'};
    ESP_ERROR_CHECK(esp_bt_gap_set_pin(ESP_BT_PIN_TYPE_FIXED, 4, pin));
    ESP_ERROR_CHECK(esp_bt_gap_set_scan_mode(ESP_BT_CONNECTABLE, ESP_BT_GENERAL_DISCOVERABLE));
    ESP_LOGI(TAG, "Bluetooth discoverable as Voice Puck V1");

    configASSERT(xTaskCreate(reconnect_task, "hfp_reconnect", 3072, NULL, 4, NULL) == pdPASS);
    xTaskCreatePinnedToCore(mic_task, "mic", 4096, NULL, 5, NULL, 1);
}
