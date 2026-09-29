#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool ready;
    bool busy;
    bool delayed;
    uint32_t disconnected_at;
} hfp_reconnect_t;

bool hfp_reconnect_poll(hfp_reconnect_t *state, uint32_t now_ms);
void hfp_reconnect_disconnected(hfp_reconnect_t *state, uint32_t now_ms);
