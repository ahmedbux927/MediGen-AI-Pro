"""Remove test files from an OLDER version of MediGen that are still in the tests folder.

Only the exact names below are deleted. Run once from the project folder:
    python scripts\\remove_old_test_files.py
"""
import os
import sys

OLD_TESTS = [
    'test_audit_log.py',
    'test_backup_unit.py',
    'test_chart_player.py',
    'test_i18n_step6.py',
    'test_settings_backup.py',
    'test_step11f_bento.py',
    'test_step11h_ultimate.py',
    'test_step11i_tactile.py',
    'test_step11j_professional.py',
    'test_step11k_professional2.py',
    'test_step11m_pages.py',
    'test_step6b_labels.py',
]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests = os.path.join(root, 'tests')
    removed, missing = [], []
    for name in OLD_TESTS:
        path = os.path.join(tests, name)
        if os.path.isfile(path):
            os.remove(path)
            removed.append(name)
        else:
            missing.append(name)
    print(f'Removed {len(removed)} old test file(s):')
    for name in removed:
        print('  -', name)
    print(f'Already gone: {len(missing)}')
    print('Next: run  python tests\\run_all.py  (expect 0 failed).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
