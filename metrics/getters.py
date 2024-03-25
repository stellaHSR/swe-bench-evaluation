import re

from log_parsers import MAP_REPO_TO_PARSER, TestStatus
from typing import Dict, List


# Evaluation Log Constants
APPLY_PATCH_FAIL = ">>>>> Patch Apply Failed"
APPLY_PATCH_PASS = ">>>>> Applied Patch"
INSTALL_FAIL = ">>>>> Init Failed"
INSTALL_PASS = ">>>>> Init Succeeded"
RESET_FAILED = ">>>>> Reset Failed"
TESTS_TIMEOUT = ">>>>> Tests Timed Out"
TESTS_ERROR = ">>>>> Tests Errored"

# Result Categories
FAIL_TO_PASS = "FAIL_TO_PASS"
FAIL_TO_FAIL = "FAIL_TO_FAIL"
PASS_TO_PASS = "PASS_TO_PASS"
PASS_TO_FAIL = "PASS_TO_FAIL"


def get_diffs(sm_1: Dict, sm_2: Dict) -> Dict:
    """
    Get differences between two test status maps

    Args:
        sm_1 (dict): test case to test status mapping
        sm_2 (dict): test case to test status mapping
    Returns:
        dict: test case to test status mapping
    """
    set1 = set(sm_1.items())
    set2 = set(sm_2.items())
    diffs = set1 ^ set2

    diff_map = {}
    for diff in diffs:
        if diff[0] not in diff_map:
            diff_map[diff[0]] = []
        diff_map[diff[0]].append(diff[1])
    return diff_map


def get_logs_eval(log_fp: str) -> (Dict, bool):
    """
    Retrieve evaluation results for a task instance from its corresponding log file

    Args:
        log_fp (str): path to log file
    Returns:
        bool: whether the patch applied successfully
        dict: status map
    """
    repo = get_repo_from_lp(log_fp)
    repo = "scikit-learn/scikit-learn"
    log_parser = MAP_REPO_TO_PARSER[repo]

    with open(log_fp, "r") as f:
        content = f.read()
        if any([x in content for x in [APPLY_PATCH_FAIL, RESET_FAILED, TESTS_ERROR, TESTS_TIMEOUT, "Failed to reset task environment"]]) or APPLY_PATCH_PASS not in content:
            # Eval patch was not applied successfully
            return {}, False

        # Get status map of evaluation results
        content = content.split(f"{APPLY_PATCH_PASS} (pred)")[-1]
        return log_parser(content), True


def get_logs_gold(log_fp: str) -> (str, str):
    """
    Retrieve pre-patch, post-patch test logs from a validation log file

    Args:
        log_fp (str): path to log file
    Returns:
        str: pre-patch, post-patch test logs
    """
    with open(log_fp, "r") as f:
        content = f.read()
        if len(re.findall(APPLY_PATCH_PASS, content)) != 2:
            return None, None
        logs = content.split(APPLY_PATCH_PASS)
        log_before, log_after = logs[1], logs[2]
        return log_before, log_after


get_file_name_from_lp = lambda x: x.rsplit("/", 1)[-1]


get_id_from_lp = lambda x: get_file_name_from_lp(x).split(".")[0]


get_repo_from_lp = lambda x: get_id_from_lp(x).rsplit("-", 1)[0].replace("__", "/")


def log_path_to_sms(log_fp: str, log_parser) -> (List, bool):
    """
    Wrapper for getting log data from log_parser file

    Args:
        log_fp (str): path to log file
        log_parser (function): function to parse log file
    Returns:
        list: list of status maps
        bool: whether or not log file was parsed properly
    """
    log_before, log_after = get_logs_gold(log_fp)
    if log_before is None and log_after is None:
        # Skip if either one of test patch apply + patch apply failed
        return None, False

    try:
        sm_before = log_parser(log_before)
        sm_after = log_parser(log_after)
    except Exception as e:
        # Skip if log file was not parsed properly
        print(f"Error parsing log {log_fp}: {e}")
        sm_before, sm_after = None, None

    if sm_before is None or sm_after is None:
        # Skip if test patch or patch statuses are none
        return None, False

    return [sm_before, sm_after], True


test_passed = lambda case, sm: case in sm and sm[case] == TestStatus.PASSED.value

test_failed = lambda case, sm: case not in sm or any(
    [sm[case] == status for status in [TestStatus.FAILED.value, TestStatus.ERROR.value]]
)
