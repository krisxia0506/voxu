#pragma once
#include <stdbool.h>
#include "esp_bt_defs.h"

// Bluedroid must be enabled first. HID follows the active HFP host.
void boot_hid_init(void);
void boot_hid_set_hfp_connected(bool connected, const uint8_t *address);
