#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "hfp_reconnect.h"

int main(void)
{
    hfp_reconnect_t state = {0};
    assert(!hfp_reconnect_poll(&state, 100)); // Never before profile initialization.
    state.ready = true;
    assert(!hfp_reconnect_poll(&state, 100)); // No previous host: wait for pairing.
    const uint8_t first[6] = {1, 2, 3, 4, 5, 6};
    const uint8_t second[6] = {6, 5, 4, 3, 2, 1};
    assert(hfp_reconnect_remember(&state, first));
    assert(!hfp_reconnect_remember(&state, first)); // Avoid rewriting flash each reconnect.
    assert(hfp_reconnect_remember(&state, second));
    assert(memcmp(state.peer, second, 6) == 0); // Latest host replaces old target.
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
