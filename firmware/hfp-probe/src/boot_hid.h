#pragma once
#include <stdbool.h>
#include "esp_bt_defs.h"

// Bluedroid must be enabled first. The probe only connects to its configured Mac.
void boot_hid_init(const uint8_t *mac);
void boot_hid_set_hfp_connected(bool connected);
