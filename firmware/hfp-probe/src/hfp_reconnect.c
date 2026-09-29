#include "hfp_reconnect.h"

bool hfp_reconnect_poll(hfp_reconnect_t *state, uint32_t now_ms)
{
    if (!state->ready || state->busy ||
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
