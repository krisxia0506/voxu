#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool raw_pressed;
    bool stable_pressed;
    bool armed;
    uint32_t changed_at;
} boot_button_t;

// Called every 10 ms. Returns one trigger per debounced press while HID is ready.
bool boot_button_poll(boot_button_t *button, bool pressed, bool ready, uint32_t now_ms);
