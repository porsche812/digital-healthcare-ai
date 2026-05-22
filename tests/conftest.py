import os
import sys

# 프로젝트 루트를 import 경로에 추가 (config, core, data ... 패키지 인식)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
