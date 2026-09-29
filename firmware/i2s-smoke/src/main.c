#include <inttypes.h>
#include <stdint.h>

#include "driver/i2s_std.h"
#include "esp_check.h"
#include "esp_log.h"

#define SAMPLE_RATE_HZ 16000
#define READ_SAMPLES 1024

static const char *TAG = "INMP441";
static int32_t samples[READ_SAMPLES];

void app_main(void)
{
    i2s_chan_handle_t rx = NULL;
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&channel, NULL, &rx));

    i2s_std_config_t config = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = GPIO_NUM_26,  // Board D26 -> microphone SCK
            .ws = GPIO_NUM_25,    // Board D25 -> microphone WS
            .dout = I2S_GPIO_UNUSED,
            .din = GPIO_NUM_33,   // Board D33 <- microphone SD
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    config.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;  // Microphone L/R -> GND

    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx, &config));
    ESP_ERROR_CHECK(i2s_channel_enable(rx));
    ESP_LOGI(TAG, "I2S RX ready: D26=SCK D25=WS D33=SD, left channel, 16 kHz");

    uint32_t blocks = 0;
    while (true) {
        size_t bytes_read = 0;
        esp_err_t err = i2s_channel_read(rx, samples, sizeof(samples), &bytes_read, 1000);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "read failed: %s", esp_err_to_name(err));
            continue;
        }

        size_t count = bytes_read / sizeof(samples[0]);
        int64_t sum_abs = 0;
        int32_t peak = 0;
        for (size_t i = 0; i < count; ++i) {
            // INMP441 returns signed 24-bit audio in a 32-bit I2S slot.
            int32_t value = samples[i] >> 8;
            int32_t magnitude = value < 0 ? -value : value;
            sum_abs += magnitude;
            if (magnitude > peak) {
                peak = magnitude;
            }
        }

        if (++blocks % 4 == 0 && count > 0) {
            ESP_LOGI(TAG, "samples=%u mean_abs=%" PRIu64 " peak=%" PRIi32,
                     (unsigned)count, (uint64_t)(sum_abs / count), peak);
        }
    }
}
