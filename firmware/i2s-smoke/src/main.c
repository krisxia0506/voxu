#include <inttypes.h>
#include <stdint.h>

#include "../../common/voxu_mic.h"
#include "esp_check.h"
#include "esp_log.h"

#define READ_SAMPLES 1024

static const char *TAG = VOXU_MIC_NAME;
static voxu_mic_sample_t samples[READ_SAMPLES];

void app_main(void)
{
    i2s_chan_handle_t rx = voxu_mic_create();
    ESP_ERROR_CHECK(i2s_channel_enable(rx));
    ESP_LOGI(TAG, "%s RX ready: 16 kHz, PCM16 diagnostic levels", VOXU_MIC_NAME);
    size_t settle_remaining = VOXU_MIC_SETTLE_SAMPLES;

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
        size_t skip = count < settle_remaining ? count : settle_remaining;
        settle_remaining -= skip;
        for (size_t i = skip; i < count; ++i) {
            int32_t value = voxu_mic_pcm16(samples[i]);
            int32_t magnitude = value < 0 ? -value : value;
            sum_abs += magnitude;
            if (magnitude > peak) {
                peak = magnitude;
            }
        }

        count -= skip;
        if (++blocks % 4 == 0 && count > 0) {
            ESP_LOGI(TAG, "samples=%u mean_abs=%" PRIu64 " peak=%" PRIi32,
                     (unsigned)count, (uint64_t)(sum_abs / count), peak);
        }
    }
}
