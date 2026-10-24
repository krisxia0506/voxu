"""Configure an external official SDK checkout for a size/build probe only.

Does not flash, obtain keys, or claim product firmware. Third-party SDK stays
outside this repository. Run on a disposable checkout at the pinned revision.
"""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('sdk', type=Path)
args = parser.parse_args()
sdk = args.sdk.resolve()
expected = 'db6737a030c01d3fef6e8045cf7c8c6df62def6e'
head = subprocess.check_output(['git', '-C', str(sdk), 'rev-parse', 'HEAD'], text=True).strip()
if head != expected:
    raise SystemExit('Unsupported SDK revision; inspect changes before applying probe')
board = sdk / 'apps/soundbox/board/br23/board_config.h'
config = sdk / 'apps/soundbox/board/br23/board_ac6955f_headset_mono/board_ac6955f_headset_mono_cfg.h'
# Construct both complete outputs before writing either file.
text = board.read_text()
text = re.sub(r'^#define CONFIG_BOARD_AC695X_DEMO\s*$',
              '// #define CONFIG_BOARD_AC695X_DEMO', text, flags=re.M)
text = re.sub(r'^//\s*#define CONFIG_BOARD_AC6955F_HEADSET_MONO\s*$',
              '#define CONFIG_BOARD_AC6955F_HEADSET_MONO', text, flags=re.M)
active = re.findall(r'^#define (CONFIG_BOARD_\w+)', text, flags=re.M)
if active != ['CONFIG_BOARD_AC6955F_HEADSET_MONO']:
    raise SystemExit(f'Unexpected board selectors: {active}')
settings = {
    'CONFIG_FLASH_SIZE': '(512 * 1024)',
    'TCFG_APP_MUSIC_EN': '0', 'TCFG_APP_LINEIN_EN': '0',
    'TCFG_SD0_ENABLE': '0', 'TCFG_SD1_ENABLE': '0',
    'TCFG_BT_SUPPORT_AAC': '0',
    'USER_SUPPORT_PROFILE_A2DP': '0', 'USER_SUPPORT_PROFILE_AVCTP': '0',
    'USER_SUPPORT_PROFILE_HFP': '1', 'USER_SUPPORT_PROFILE_HID': '1',
    'TCFG_CLOCK_OSC_HZ': '24000000',
    'TRANS_DATA_EN': '0',
    'TCFG_ENC_MSBC_ENABLE': '1', 'TCFG_ENC_CVSD_ENABLE': '1',
}
for codec in ('MP3', 'WMA', 'WAV', 'FLAC', 'APE', 'M4A', 'AMR', 'DTS'):
    settings[f'TCFG_DEC_{codec}_ENABLE'] = '0'
for codec in ('G726', 'MP3', 'ADPCM', 'PCM', 'SBC'):
    settings[f'TCFG_ENC_{codec}_ENABLE'] = '0'
cfg = config.read_text()
for name, value in settings.items():
    cfg, count = re.subn(r'^#define\s+' + name + r'\s+[^\n]+$',
                         f'#define {name} {value} // VOXU build/size probe', cfg, flags=re.M)
    if count != 1:
        raise SystemExit(f'Expected exactly one definition for {name}, got {count}')
# Fast Pair demo is independently enabled even when AI_APP_PROTOCOL is off.
protocol = sdk / 'apps/common/third_party_profile/interface/app_protocol_api.h'
proto, count = re.subn(r'^#define\s+APP_PROTOCOL_GFPS_CODE\s+[^\n]+$',
                       '#define APP_PROTOCOL_GFPS_CODE 0 // VOXU: no Fast Pair demo',
                       protocol.read_text(), flags=re.M)
if count != 1:
    raise SystemExit('Expected one Fast Pair configuration')
protocol.write_text(proto)
board.write_text(text)
config.write_text(cfg)
print('Configured HFP/HID/mSBC 512KiB probe; no firmware download performed')
