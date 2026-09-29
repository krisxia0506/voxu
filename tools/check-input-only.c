#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int device_name(AudioDeviceID device, char *buffer, size_t capacity)
{
    AudioObjectPropertyAddress property = {
        kAudioObjectPropertyName,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain,
    };
    CFStringRef value = NULL;
    UInt32 size = sizeof(value);
    if (AudioObjectGetPropertyData(device, &property, 0, NULL, &size, &value) != noErr || !value) {
        return 0;
    }
    int converted = CFStringGetCString(value, buffer, capacity, kCFStringEncodingUTF8);
    CFRelease(value);
    return converted;
}

static int channel_count(AudioDeviceID device, AudioObjectPropertyScope scope, unsigned *count)
{
    AudioObjectPropertyAddress property = {
        kAudioDevicePropertyStreamConfiguration,
        scope,
        kAudioObjectPropertyElementMain,
    };
    UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(device, &property, 0, NULL, &size) != noErr || size == 0) {
        return 0;
    }
    AudioBufferList *buffers = malloc(size);
    if (!buffers) {
        return 0;
    }
    OSStatus status = AudioObjectGetPropertyData(device, &property, 0, NULL, &size, buffers);
    if (status == noErr) {
        *count = 0;
        for (UInt32 index = 0; index < buffers->mNumberBuffers; ++index) {
            *count += buffers->mBuffers[index].mNumberChannels;
        }
    }
    free(buffers);
    return status == noErr;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <exact CoreAudio device name>\n", argv[0]);
        return 2;
    }

    AudioObjectPropertyAddress property = {
        kAudioHardwarePropertyDevices,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain,
    };
    UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &property, 0, NULL, &size) != noErr || size == 0) {
        fprintf(stderr, "Cannot read CoreAudio device list\n");
        return 2;
    }
    AudioDeviceID *devices = malloc(size);
    if (!devices) {
        return 2;
    }
    if (AudioObjectGetPropertyData(kAudioObjectSystemObject, &property, 0, NULL, &size, devices) != noErr) {
        free(devices);
        fprintf(stderr, "Cannot read CoreAudio devices\n");
        return 2;
    }

    unsigned input_devices = 0;
    unsigned output_devices = 0;
    for (UInt32 index = 0; index < size / sizeof(AudioDeviceID); ++index) {
        char name[256] = {0};
        if (!device_name(devices[index], name, sizeof(name)) || strcmp(name, argv[1]) != 0) {
            continue;
        }
        unsigned inputs = 0;
        unsigned outputs = 0;
        if (!channel_count(devices[index], kAudioObjectPropertyScopeInput, &inputs) ||
            !channel_count(devices[index], kAudioObjectPropertyScopeOutput, &outputs)) {
            AudioDeviceID failed_device = devices[index];
            free(devices);
            fprintf(stderr, "Cannot inspect channels for device %u\n", failed_device);
            return 2;
        }
        printf("device=%u input_channels=%u output_channels=%u name=%s\n",
               devices[index], inputs, outputs, name);
        input_devices += inputs > 0;
        output_devices += outputs > 0;
    }
    free(devices);

    printf("matching_input_devices=%u matching_output_devices=%u\n", input_devices, output_devices);
    if (input_devices == 0 || output_devices != 0) {
        fprintf(stderr, "FAIL: %s is not input-only\n", argv[1]);
        return 1;
    }
    printf("PASS: %s appears only as an input device\n", argv[1]);
    return 0;
}
