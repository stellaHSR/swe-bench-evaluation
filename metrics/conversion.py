import json, os

from log_parsers import MAP_REPO_TO_PARSER, TestStatus
from typing import Dict, List
from getters import (
    get_file_name_from_lp,
    get_repo_from_lp,
    log_path_to_sms,
    FAIL_TO_PASS,
    FAIL_TO_FAIL,
    PASS_TO_PASS,
    PASS_TO_FAIL,
    test_failed,
    test_passed,
)


def convert_log_to_ground_truth(
    log_fp: List, save_dir: str = None, verbose: bool = False
) -> Dict:
    """
    Convert log file generated from check instances into ground truth dict

    Args:
        log_dir (str): path to log files
        save_dir (str): path to save results
        verbose (bool): whether or not to show logs
    Returns:
        dict: test case to test status mapping
    """
    inst_file_name = get_file_name_from_lp(log_fp)
    repo = get_repo_from_lp(log_fp)
    log_parser = MAP_REPO_TO_PARSER[repo]

    sms, found = log_path_to_sms(log_fp, log_parser)
    if not found:
        raise ValueError(
            "Log file could not be parsed properly (Before, After Logs not found)"
        )
    sm_before, sm_after = sms[0], sms[1]

    status_ground_truth = {
        FAIL_TO_PASS: [],
        FAIL_TO_FAIL: [],
        PASS_TO_PASS: [],
        PASS_TO_FAIL: [],
    }

    for test, status in sm_after.items():
        if status == TestStatus.PASSED.value:
            if test_passed(test, sm_before):
                status_ground_truth[PASS_TO_PASS].append(test)
            elif test_failed(test, sm_before):
                status_ground_truth[FAIL_TO_PASS].append(test)
        if status == TestStatus.FAILED.value:
            if test_passed(test, sm_before):
                status_ground_truth[PASS_TO_FAIL].append(test)
            elif test_failed(test, sm_before):
                status_ground_truth[FAIL_TO_FAIL].append(test)

    if save_dir is not None:
        results_file = f"{inst_file_name.split('.')[0]}.json"
        if verbose:
            print(f"Saving results to {os.path.join(save_dir, results_file)}")
        with open(os.path.join(save_dir, results_file), "w") as f:
            json.dump(status_ground_truth, f, indent=4)

    return status_ground_truth
