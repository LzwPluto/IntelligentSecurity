import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.asr import sensevoice_rknn

args = sensevoice_rknn.parse_args()
sensevoice_rknn.main(args.audio_file, args.download_path, args.device, args.num_threads, args.language, args.use_itn)
