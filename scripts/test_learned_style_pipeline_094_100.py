from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.learned_style_pipeline.pipeline import (
    create_apply_style_profile,
    create_learned_source_scorer,
    create_profile_story_timeline_builder,
    create_profile_rhythm_retimer,
    create_learned_inout_picker,
    create_profile_music_sync_bridge,
    create_learned_profile_xml_exporter,
)
def main():
    print("Modules import OK: 094-100 Learned Style Pipeline")
    print(create_apply_style_profile)
    print(create_learned_source_scorer)
    print(create_profile_story_timeline_builder)
    print(create_profile_rhythm_retimer)
    print(create_learned_inout_picker)
    print(create_profile_music_sync_bridge)
    print(create_learned_profile_xml_exporter)
if __name__ == "__main__":
    main()
