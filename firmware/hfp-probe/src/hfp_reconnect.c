#include "hfp_reconnect.h"
#include <string.h>

bool hfp_reconnect_poll(hfp_reconnect_t *state, uint32_t now_ms)
{
    if (!state->ready || !state->has_peer || state->busy ||
        (state->delayed && (uint32_t)(now_ms - state->disconnected_at) < 5000)) {
        return false;
    }
    state->busy = true;
    state->attempt_started = now_ms;
    return true;
}

void hfp_reconnect_disconnected(hfp_reconnect_t *state, uint32_t now_ms)
{
    state->busy = false;
    state->connected = false;
    state->delayed = true;
    state->disconnected_at = now_ms;
}

bool hfp_reconnect_remember(hfp_reconnect_t *state, const uint8_t peer[6])
{
    if (state->has_peer && memcmp(state->peer, peer, 6) == 0) return false;
    memcpy(state->peer, peer, 6);
    state->has_peer = true;
    return true;
}

bool hfp_reconnect_stalled(const hfp_reconnect_t *state, uint32_t now_ms)
{
    return state->ready && state->has_peer && state->busy && !state->connected &&
           (uint32_t)(now_ms - state->attempt_started) >= 60000;
}
