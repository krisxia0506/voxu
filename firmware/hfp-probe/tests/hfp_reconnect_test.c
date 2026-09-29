#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "hfp_reconnect.h"

int main(void)
{
    hfp_reconnect_t state = {0};
    assert(!hfp_reconnect_poll(&state, 100)); // Never before profile initialization.
    state.ready = true;
    assert(hfp_reconnect_poll(&state, 100)); // No inquiry/host discoverability needed.
    assert(!hfp_reconnect_poll(&state, 60000)); // One outstanding request only.
    hfp_reconnect_disconnected(&state, 60000); // Async failure or link loss.
    assert(!hfp_reconnect_poll(&state, 64999));
    assert(hfp_reconnect_poll(&state, 65000));
    hfp_reconnect_disconnected(&state, 65000); // Immediate API rejection also retries.
    assert(hfp_reconnect_poll(&state, 70000));
    state.busy = true; // Incoming RFCOMM / SLC connection suppresses attempts.
    assert(!hfp_reconnect_poll(&state, 90000));
    hfp_reconnect_disconnected(&state, UINT32_MAX - 1000);
    assert(!hfp_reconnect_poll(&state, 3998));
    assert(hfp_reconnect_poll(&state, 3999)); // Millisecond counter rollover.
    puts("hfp reconnect tests passed");
}
