#include "hfp_reconnect.h"
#include <string.h>

bool hfp_reconnect_poll(hfp_reconnect_t *state, uint32_t now_ms)
{
    if (!state->ready || !state->has_peer || state->busy ||
        (state->delayed && (uint32_t)(now_ms - state->disconnected_at) < 5000)) {
        return false;
    }
    state->busy = true;
    return true;
}

void hfp_reconnect_disconnected(hfp_reconnect_t *state, uint32_t now_ms)
{
    state->busy = false;
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
