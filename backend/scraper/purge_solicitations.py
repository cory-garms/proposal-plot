"""
Solicitation DB purge — four phases.

Usage:
    python -m backend.scraper.purge_solicitations          # dry run
    python -m backend.scraper.purge_solicitations --commit # actually delete

Phases:
  1. Expired SAM records that were never scored and never watched
  2. SAM duplicates by topic_number — keep the copy with the most scores (highest id breaks tie)
  3. Expired SBIR.gov records (all old dev data)
  4. SAM records where every capability scored 0 (keyword filter found nothing) and not watched

No CASCADE is set on solicitation_capability_scores.solicitation_id, so scores are
deleted explicitly before their parent solicitation rows.
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.database import get_connection


def _count(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def phase1_expired_unscored_sam(conn, commit: bool) -> int:
    ids = [r[0] for r in conn.execute("""
        SELECT s.id FROM solicitations s
        WHERE s.source = 'sam'
          AND s.close_date < date('now')
          AND s.watched = 0
          AND NOT EXISTS (
              SELECT 1 FROM solicitation_capability_scores sc
              WHERE sc.solicitation_id = s.id
          )
    """)]
    print(f"  Phase 1: {len(ids)} expired unscored unwatched SAM rows")
    if commit and ids:
        placeholders = ",".join("?" * len(ids))
        # No scores to delete (unscored by definition)
        conn.execute(f"DELETE FROM solicitations WHERE id IN ({placeholders})", ids)
    return len(ids)


def phase2_sam_dedup(conn, commit: bool) -> int:
    # For each topic_number group with duplicates, find the row to KEEP:
    # highest score_count, then highest id (most recent).
    keep_ids = set(r[0] for r in conn.execute("""
        WITH ranked AS (
            SELECT s.id,
                   COUNT(sc.solicitation_id) AS score_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY s.topic_number
                       ORDER BY COUNT(sc.solicitation_id) DESC, s.id DESC
                   ) AS rn
            FROM solicitations s
            LEFT JOIN solicitation_capability_scores sc ON sc.solicitation_id = s.id
            WHERE s.source = 'sam'
              AND s.topic_number IS NOT NULL AND s.topic_number != ''
            GROUP BY s.id, s.topic_number
        )
        SELECT id FROM ranked WHERE rn = 1
    """))

    delete_ids = [r[0] for r in conn.execute("""
        SELECT id FROM solicitations
        WHERE source = 'sam'
          AND topic_number IS NOT NULL AND topic_number != ''
    """) if r[0] not in keep_ids]

    print(f"  Phase 2: {len(delete_ids)} duplicate SAM rows (keeping {len(keep_ids)} unique topic_numbers)")
    if commit and delete_ids:
        placeholders = ",".join("?" * len(delete_ids))
        conn.execute(f"DELETE FROM solicitation_capability_scores WHERE solicitation_id IN ({placeholders})", delete_ids)
        conn.execute(f"DELETE FROM solicitations WHERE id IN ({placeholders})", delete_ids)
    return len(delete_ids)


def phase3_expired_sbir(conn, commit: bool) -> int:
    ids = [r[0] for r in conn.execute("""
        SELECT id FROM solicitations WHERE source = 'sbir'
    """)]
    score_count = _count(conn, f"""
        SELECT COUNT(*) FROM solicitation_capability_scores
        WHERE solicitation_id IN ({','.join('?' * len(ids))})
    """, ids) if ids else 0
    print(f"  Phase 3: {len(ids)} SBIR.gov rows ({score_count} score entries)")
    if commit and ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM solicitation_capability_scores WHERE solicitation_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM solicitations WHERE id IN ({placeholders})", ids)
    return len(ids)


def phase4_zero_score_sam(conn, commit: bool) -> int:
    """SAM records where all capability scores are 0 (keyword filter found nothing), not watched."""
    ids = [r[0] for r in conn.execute("""
        SELECT s.id FROM solicitations s
        WHERE s.source = 'sam'
          AND s.watched = 0
          AND EXISTS (
              SELECT 1 FROM solicitation_capability_scores sc
              WHERE sc.solicitation_id = s.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM solicitation_capability_scores sc
              WHERE sc.solicitation_id = s.id AND sc.score > 0
          )
    """)]
    score_count = _count(conn, f"""
        SELECT COUNT(*) FROM solicitation_capability_scores
        WHERE solicitation_id IN ({','.join('?' * len(ids))})
    """, ids) if ids else 0
    print(f"  Phase 4: {len(ids)} zero-score SAM rows ({score_count} score entries — all 0.00)")
    if commit and ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM solicitation_capability_scores WHERE solicitation_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM solicitations WHERE id IN ({placeholders})", ids)
    return len(ids)


def run(commit: bool):
    conn = get_connection()
    total_before = _count(conn, "SELECT COUNT(*) FROM solicitations")
    scores_before = _count(conn, "SELECT COUNT(*) FROM solicitation_capability_scores")
    print(f"Before: {total_before} solicitations, {scores_before} score entries")
    print(f"Mode:   {'COMMIT' if commit else 'DRY RUN'}\n")

    if commit:
        # Run sequentially — each phase only sees rows still present
        phase1_expired_unscored_sam(conn, commit)
        phase2_sam_dedup(conn, commit)
        phase3_expired_sbir(conn, commit)
        phase4_zero_score_sam(conn, commit)
        conn.commit()
        total_after = _count(conn, "SELECT COUNT(*) FROM solicitations")
        scores_after = _count(conn, "SELECT COUNT(*) FROM solicitation_capability_scores")
        print(f"\nAfter:  {total_after} solicitations, {scores_after} score entries")
        print(f"Removed: {total_before - total_after} solicitations, {scores_before - scores_after} score entries")
    else:
        # Dry run: collect all IDs across phases and deduplicate for an accurate projection
        p1_ids = set(r[0] for r in conn.execute("""
            SELECT s.id FROM solicitations s
            WHERE s.source='sam' AND s.close_date < date('now') AND s.watched=0
            AND NOT EXISTS (SELECT 1 FROM solicitation_capability_scores sc WHERE sc.solicitation_id=s.id)
        """))

        keep_ids = set(r[0] for r in conn.execute("""
            WITH ranked AS (
                SELECT s.id,
                       COUNT(sc.solicitation_id) AS score_count,
                       ROW_NUMBER() OVER (
                           PARTITION BY s.topic_number
                           ORDER BY COUNT(sc.solicitation_id) DESC, s.id DESC
                       ) AS rn
                FROM solicitations s
                LEFT JOIN solicitation_capability_scores sc ON sc.solicitation_id=s.id
                WHERE s.source='sam' AND s.topic_number IS NOT NULL AND s.topic_number!=''
                GROUP BY s.id, s.topic_number
            ) SELECT id FROM ranked WHERE rn=1
        """))
        p2_ids = set(r[0] for r in conn.execute("""
            SELECT id FROM solicitations
            WHERE source='sam' AND topic_number IS NOT NULL AND topic_number!=''
        """) if r[0] not in keep_ids)

        p3_ids = set(r[0] for r in conn.execute("SELECT id FROM solicitations WHERE source='sbir'"))

        p4_ids = set(r[0] for r in conn.execute("""
            SELECT s.id FROM solicitations s
            WHERE s.source='sam' AND s.watched=0
            AND EXISTS (SELECT 1 FROM solicitation_capability_scores sc WHERE sc.solicitation_id=s.id)
            AND NOT EXISTS (SELECT 1 FROM solicitation_capability_scores sc WHERE sc.solicitation_id=s.id AND sc.score>0)
        """))

        all_delete = p1_ids | p2_ids | p3_ids | p4_ids
        print(f"  Phase 1: {len(p1_ids)} rows")
        print(f"  Phase 2: {len(p2_ids)} rows")
        print(f"  Phase 3: {len(p3_ids)} rows")
        print(f"  Phase 4: {len(p4_ids)} rows  ({len(p4_ids & p2_ids)} overlap with Phase 2)")
        print(f"\n  Unique rows to delete: {len(all_delete)}")
        print(f"  Projected after commit: {total_before - len(all_delete)} solicitations")
        print("\nRun with --commit to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Actually delete rows (default is dry run)")
    args = parser.parse_args()
    run(commit=args.commit)
