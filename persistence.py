"""CSV 영속성: 저장 전 백업 → 원자적 쓰기 → 백업 회전. (streamlit 비의존, 테스트 용이)"""
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "Data"
BACKUP_DIR = DATA_DIR / "backups"


def backup_then_atomic_write(df: pd.DataFrame, target: Path, cols=None) -> Path | None:
    """target 을 백업한 뒤 df 를 원자적으로 덮어쓴다. 생성된 백업 경로(없으면 None) 반환.

    - 백업: Data/backups/<name>_YYYYMMDD-HHMMSS.csv (대상 파일이 이미 있을 때만)
    - 쓰기: 같은 디렉터리 임시파일 → os.replace 로 원자 교체 (utf-8-sig, BOM 유지)
    """
    target = Path(target)
    cols = list(cols) if cols is not None else list(df.columns)

    backup_path = None
    if target.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = BACKUP_DIR / f"{target.stem}_{stamp}{target.suffix}"
        shutil.copy2(target, backup_path)

    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.stem}_", suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        df.to_csv(tmp_path, index=False, columns=cols, encoding="utf-8-sig")
        os.replace(tmp_path, target)
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    return backup_path


def prune_backups(name: str, keep: int = 20) -> int:
    """name 접두(파일 stem) 백업을 최신 keep 개만 남기고 삭제. 삭제 개수 반환."""
    if not BACKUP_DIR.exists():
        return 0
    files = sorted(
        BACKUP_DIR.glob(f"{name}_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    for p in files[keep:]:
        p.unlink(missing_ok=True)
        removed += 1
    return removed


def file_mtime(target: Path) -> float | None:
    """저장 직전 동시편집 가드용. 파일 없으면 None."""
    target = Path(target)
    return target.stat().st_mtime if target.exists() else None
