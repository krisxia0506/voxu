#pragma once

#include <stdint.h>
#include "esp_check.h"

#define VOXU_MIC_RATE_HZ 16000

#if defined(VOXU_MIC_SPH0655)
#include "driver/i2s_pdm.h"
typedef int16_t voxu_mic_sample_t;
#define VOXU_MIC_NAME "SPH0655 PDM"
// Rev D specifies up to 35 ms startup/wakeup; discard 40 ms on each enable.
#define VOXU_MIC_SETTLE_SAMPLES (VOXU_MIC_RATE_HZ * 40 / 1000)
static inline int16_t voxu_mic_pcm16(voxu_mic_sample_t sample) { return sample; }
#else
#include "driver/i2s_std.h"
typedef int32_t voxu_mic_sample_t;
#define VOXU_MIC_NAME "INMP441 I2S"
#define VOXU_MIC_SETTLE_SAMPLES 0
static inline int16_t voxu_mic_pcm16(voxu_mic_sample_t sample) { return sample >> 16; }
#endif

// Returns a configured, disabled receiver. The caller owns enable/disable/read.
static inline i2s_chan_handle_t voxu_mic_create(void)
{
    i2s_chan_handle_t rx = NULL;
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&channel, NULL, &rx));
#if defined(VOXU_MIC_SPH0655)
    i2s_pdm_rx_config_t config = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(VOXU_MIC_RATE_HZ),
        .slot_cfg = I2S_PDM_RX_SLOT_PCM_FMT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .clk = GPIO_NUM_26,
            .din = GPIO_NUM_33,
            .invert_flags = { .clk_inv = false },
        },
    };
    // 16 kHz * 128 = 2.048 MHz, inside SPH0655 normal mode (1.1–4.8 MHz).
    // The default 64x clock is 1.024 MHz, outside both specified active modes.
    config.clk_cfg.dn_sample_mode = I2S_PDM_DSR_16S;
    // SELECT is grounded. Follow ESP-IDF's non-S3 PDM microphone example.
    config.slot_cfg.slot_mask = I2S_PDM_SLOT_LEFT;
    ESP_ERROR_CHECK(i2s_channel_init_pdm_rx_mode(rx, &config));
#else
    i2s_std_config_t config = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(VOXU_MIC_RATE_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO),
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
#endif
    return rx;
}
