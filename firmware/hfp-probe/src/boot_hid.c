#include "boot_hid.h"
#include "boot_button.h"
#include <string.h>
#include "driver/gpio.h"
#include "esp_hidd_api.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"

static const char *TAG = "BOOT_HID";
// Standard eight-byte keyboard input report, no report ID; includes F13 (0x68).
static uint8_t descriptor[] = {
    0x05, 0x01, 0x09, 0x06, 0xa1, 0x01,
    0x05, 0x07, 0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
    0x75, 0x08, 0x95, 0x01, 0x81, 0x03,
    0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x75, 0x01, 0x95, 0x05, 0x91, 0x02,
    0x75, 0x03, 0x95, 0x01, 0x91, 0x03,
    0x05, 0x07, 0x19, 0x00, 0x29, 0x73, 0x15, 0x00, 0x25, 0x73,
    0x75, 0x08, 0x95, 0x06, 0x81, 0x00, 0xc0,
};
static esp_hidd_app_param_t app = {
    .name = "Voice Puck BOOT keyboard",
    .description = "Typeless Control Option Shift Command F13",
    .provider = "Voice Puck",
    .subclass = ESP_HID_CLASS_KBD,
    .desc_list = descriptor,
    .desc_list_len = sizeof(descriptor),
};
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static bool registered, connected, connecting, hfp_connected, unplugged;
static unsigned generation;
static uint8_t protocol = ESP_HIDD_REPORT_MODE;
static uint8_t report[8];
static uint8_t leds;
static esp_bd_addr_t peer;
static SemaphoreHandle_t completion;
static esp_hidd_status_t send_status;
typedef struct {
    esp_hidd_report_type_t type;
    uint8_t id, len, data[8];
    unsigned epoch;
} control_report_t;
static QueueHandle_t control_reports;

void boot_hid_set_hfp_connected(bool up)
{
    portENTER_CRITICAL(&lock);
    hfp_connected = up;
    portEXIT_CRITICAL(&lock);
}

static void disconnected(void)
{
    portENTER_CRITICAL(&lock);
    connected = false;
    connecting = false;
    memset(report, 0, sizeof(report));
    ++generation;
    portEXIT_CRITICAL(&lock);
}

static void hid_callback(esp_hidd_cb_event_t event, esp_hidd_cb_param_t *param)
{
    switch (event) {
    case ESP_HIDD_INIT_EVT:
        if (param->init.status == ESP_HIDD_SUCCESS) {
            ESP_ERROR_CHECK(esp_bt_hid_device_register_app(&app, NULL, NULL));
        } else {
            ESP_LOGE(TAG, "HID init failed: %d", param->init.status);
        }
        break;
    case ESP_HIDD_REGISTER_APP_EVT:
        portENTER_CRITICAL(&lock);
        registered = param->register_app.status == ESP_HIDD_SUCCESS;
        portEXIT_CRITICAL(&lock);
        ESP_LOGI(TAG, "HID registered status=%d", param->register_app.status);
        break;
    case ESP_HIDD_OPEN_EVT:
        ESP_LOGI(TAG, "HID open status=%d state=%d", param->open.status, param->open.conn_status);
        if (param->open.status == ESP_HIDD_SUCCESS &&
            param->open.conn_status == ESP_HIDD_CONN_STATE_CONNECTED) {
            portENTER_CRITICAL(&lock);
            connected = true;
            connecting = false;
            unplugged = false;
            protocol = ESP_HIDD_REPORT_MODE;
            memset(report, 0, sizeof(report));
            ++generation;
            portEXIT_CRITICAL(&lock);
        } else if (param->open.status != ESP_HIDD_SUCCESS ||
                   param->open.conn_status == ESP_HIDD_CONN_STATE_DISCONNECTED) {
            disconnected();
        }
        break;
    case ESP_HIDD_CLOSE_EVT:
        ESP_LOGI(TAG, "HID close status=%d state=%d", param->close.status, param->close.conn_status);
        if (param->close.conn_status == ESP_HIDD_CONN_STATE_DISCONNECTED) disconnected();
        break;
    case ESP_HIDD_VC_UNPLUG_EVT:
        disconnected();
        portENTER_CRITICAL(&lock);
        unplugged = true; // Respect host removal; reconnect manually or restart the probe.
        portEXIT_CRITICAL(&lock);
        break;
    case ESP_HIDD_SEND_REPORT_EVT:
        // ESP-IDF normalizes INTRDATA to INPUT in completion callbacks.
        // All data reports (including GET_REPORT replies) are serialized by the task.
        portENTER_CRITICAL(&lock);
        send_status = param->send_report.status;
        portEXIT_CRITICAL(&lock);
        xSemaphoreGive(completion);
        break;
    case ESP_HIDD_SET_PROTOCOL_EVT:
        portENTER_CRITICAL(&lock);
        protocol = param->set_protocol.protocol_mode;
        portEXIT_CRITICAL(&lock);
        break;
    case ESP_HIDD_GET_REPORT_EVT: {
        uint8_t data[8], id;
        portENTER_CRITICAL(&lock);
        id = protocol == ESP_HIDD_BOOT_MODE ? ESP_HIDD_BOOT_REPORT_ID_KEYBOARD : 0;
        memcpy(data, report, sizeof(data));
        uint8_t output = leds;
        unsigned epoch = generation;
        portEXIT_CRITICAL(&lock);
        if (param->get_report.report_id != id) {
            esp_bt_hid_device_report_error(ESP_HID_PAR_HANDSHAKE_RSP_ERR_INVALID_REP_ID);
            break;
        }
        unsigned len = sizeof(data);
        if (param->get_report.report_type == ESP_HIDD_REPORT_TYPE_OUTPUT) {
            data[0] = output;
            len = 1;
        } else if (param->get_report.report_type != ESP_HIDD_REPORT_TYPE_INPUT) {
            esp_bt_hid_device_report_error(ESP_HID_PAR_HANDSHAKE_RSP_ERR_UNSUPPORTED_REQ);
            break;
        }
        if (param->get_report.buffer_size && param->get_report.buffer_size < len) {
            len = param->get_report.buffer_size;
        }
        control_report_t reply = {.type = param->get_report.report_type, .id = id, .len = len, .epoch = epoch};
        memcpy(reply.data, data, len);
        if (xQueueSend(control_reports, &reply, 0) != pdTRUE) {
            esp_bt_hid_device_report_error(ESP_HID_PAR_HANDSHAKE_RSP_NOT_READY);
        }
        break;
    }
    case ESP_HIDD_SET_REPORT_EVT: {
        portENTER_CRITICAL(&lock);
        uint8_t id = protocol == ESP_HIDD_BOOT_MODE ? ESP_HIDD_BOOT_REPORT_ID_KEYBOARD : 0;
        bool valid = param->set_report.report_type == ESP_HIDD_REPORT_TYPE_OUTPUT &&
                     param->set_report.report_id == id && param->set_report.len == 1;
        if (valid) leds = param->set_report.data[0];
        portEXIT_CRITICAL(&lock);
        esp_bt_hid_device_report_error(valid ? ESP_HID_PAR_HANDSHAKE_RSP_SUCCESS :
                                              ESP_HID_PAR_HANDSHAKE_RSP_ERR_INVALID_PARAM);
        break;
    }
    default:
        break;
    }
}

// Only the button task sends data reports, with one outstanding at a time.
static bool send_report(esp_hidd_report_type_t type, uint8_t id, uint8_t *data, size_t len)
{
    xSemaphoreTake(completion, 0);
    portENTER_CRITICAL(&lock);
    bool up = connected;
    unsigned epoch = generation;
    portEXIT_CRITICAL(&lock);
    if (!up) return false;
    esp_err_t err = esp_bt_hid_device_send_report(type, id, len, data);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "report enqueue failed: %s", esp_err_to_name(err));
        return false;
    }
    if (xSemaphoreTake(completion, pdMS_TO_TICKS(1000)) != pdTRUE) {
        // Do not match a late completion to another report. Drop this HID link.
        ESP_LOGE(TAG, "report timed out; disconnecting HID to clear held keys");
        esp_bt_hid_device_disconnect();
        disconnected();
        return false;
    }
    portENTER_CRITICAL(&lock);
    bool ok = send_status == ESP_HIDD_SUCCESS && connected && epoch == generation;
    portEXIT_CRITICAL(&lock);
    return ok;
}

static bool send_keys(bool down)
{
    uint8_t data[8] = {0};
    if (down) { data[0] = 0x0f; data[2] = 0x68; } // left Ctrl+Shift+Alt+GUI, F13
    portENTER_CRITICAL(&lock);
    uint8_t id = protocol == ESP_HIDD_BOOT_MODE ? ESP_HIDD_BOOT_REPORT_ID_KEYBOARD : 0;
    memcpy(report, data, sizeof(report));
    portEXIT_CRITICAL(&lock);
    bool ok = send_report(ESP_HIDD_REPORT_TYPE_INTRDATA, id, data, sizeof(data));
    ESP_LOGI(TAG, "shortcut %s: %s", down ? "down" : "up", ok ? "sent" : "failed");
    return ok;
}

static void button_task(void *arg)
{
    (void)arg;
    boot_button_t button = {0};
    unsigned seen_generation = 0;
    bool clean = false;
    TickType_t last_connect = 0;
    while (true) {
        TickType_t now = xTaskGetTickCount();
        portENTER_CRITICAL(&lock);
        bool up = connected;
        unsigned epoch = generation;
        bool can_connect = registered && hfp_connected && !connected && !connecting && !unplugged;
        portEXIT_CRITICAL(&lock);
        if (can_connect && now - last_connect >= pdMS_TO_TICKS(5000)) {
            last_connect = now;
            portENTER_CRITICAL(&lock);
            connecting = true;
            portEXIT_CRITICAL(&lock);
            esp_err_t err = esp_bt_hid_device_connect(peer);
            ESP_LOGI(TAG, "connect HID to test Mac: %s", esp_err_to_name(err));
            if (err != ESP_OK) {
                portENTER_CRITICAL(&lock);
                connecting = false;
                portEXIT_CRITICAL(&lock);
            }
        }
        if (!up || epoch != seen_generation) {
            clean = false;
            button.armed = false;
            seen_generation = epoch;
        }
        control_report_t reply;
        while (xQueueReceive(control_reports, &reply, 0) == pdTRUE) {
            if (up && reply.epoch == epoch) send_report(reply.type, reply.id, reply.data, reply.len);
        }
        if (up && !clean) {
            clean = send_keys(false); // clear modifiers on connection and after any failed release
            if (!clean) vTaskDelay(pdMS_TO_TICKS(100));
        }
        if (boot_button_poll(&button, gpio_get_level(GPIO_NUM_0) == 0, up && clean,
                             xTaskGetTickCount() * portTICK_PERIOD_MS)) {
            ESP_LOGI(TAG, "BOOT pressed: Ctrl+Option+Shift+Command+F13");
            if (send_keys(true)) vTaskDelay(pdMS_TO_TICKS(80));
            clean = send_keys(false); // Always release, even if key-down completion failed.
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void boot_hid_init(const uint8_t *mac)
{
    memcpy(peer, mac, sizeof(peer));
    completion = xSemaphoreCreateBinary();
    configASSERT(completion);
    control_reports = xQueueCreate(4, sizeof(control_report_t));
    configASSERT(control_reports);
    gpio_config_t pin = {
        .pin_bit_mask = 1ULL << GPIO_NUM_0,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&pin));
    ESP_ERROR_CHECK(esp_bt_hid_device_register_callback(hid_callback));
    ESP_ERROR_CHECK(esp_bt_hid_device_init());
    configASSERT(xTaskCreate(button_task, "boot_hid", 4096, NULL, 4, NULL) == pdPASS);
    ESP_LOGI(TAG, "BOOT GPIO0 ready; shortcut Ctrl+Option+Shift+Command+F13, tap to toggle");
}
