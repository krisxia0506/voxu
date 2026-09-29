#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint8_t peer[6];
    bool has_peer;
    bool ready;
    bool busy;
    bool connected;
    uint32_t attempt_started;
    bool delayed;
    uint32_t disconnected_at;
} hfp_reconnect_t;

bool hfp_reconnect_poll(hfp_reconnect_t *state, uint32_t now_ms);
void hfp_reconnect_disconnected(hfp_reconnect_t *state, uint32_t now_ms);

// Returns true only when the last connected host changes.
bool hfp_reconnect_remember(hfp_reconnect_t *state, const uint8_t peer[6]);

// Recover a lower-stack request that never completed, not a healthy connection.
bool hfp_reconnect_stalled(const hfp_reconnect_t *state, uint32_t now_ms);
