#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import re
import pandas as pd
import metrics
from lib import make_metrics, set_logger
from lib.logger import Logger as logger


def _get_latest_eval_datetime():
    date_names = [path for path in Path('./results/sets/').glob('*') if re.search(r'\d+', str(path))]
    latest = max(date_names, key=lambda date_name: date_name.stat().st_mtime).name
    return latest


def check_eval_options():
    parser = argparse.ArgumentParser(description='Options for eval')
    parser.add_argument('--eval_datetime', type=str, default=None, help='date time for evaluation(Default: None)')
    args = parser.parse_args()

    # Check date time
    if args.eval_datetime is None:
        args.eval_datetime = _get_latest_eval_datetime()
    return args


def _collect_likelihood(eval_datetime):
    likelihood_paths = list(Path('./results/sets/', eval_datetime, 'likelihoods').glob('likelihood_*.csv'))
    assert likelihood_paths != [], f"No likelihood for {eval_datetime}."
    likelihood_paths.sort(key=lambda path: path.stat().st_mtime)
    return likelihood_paths


def _check_task(eval_datetime):
    parameter_path = Path('./results/sets', eval_datetime, 'parameter.csv')
    df_args = pd.read_csv(parameter_path)
    task = df_args.loc[df_args['option'] == 'task', 'parameter'].item()
    return task


def _set_eval(task):
    if task == 'classification':
        return metrics.make_roc, 'ROC'
    elif task == 'regression':
        return metrics.make_yy, 'YY'
    elif task == 'deepsurv':
        return metrics.make_c_index, 'C_Index'
    else:
        logger.logger.error(f"Invalid task: {task}.")
        exit()


def update_summary(df_summary):
    summary_dir = Path('./results/summary')
    summary_path = Path(summary_dir, 'summary.csv')
    if summary_path.exists():
        df_prev = pd.read_csv(summary_path)
        df_updated = pd.concat([df_prev, df_summary], axis=0)
    else:
        summary_dir.mkdir(parents=True, exist_ok=True)
        df_updated = df_summary
    df_updated.to_csv(summary_path, index=False)


def main(args):
    eval_datetime = args.eval_datetime
    likelihood_paths = _collect_likelihood(eval_datetime)
    task = _check_task(eval_datetime)
    #make_eval, _metrics = _set_eval(task)
    make_eval, _metrics = make_metrics(task)

    logger.logger.info(f"Calculating {_metrics} for {eval_datetime}.\n")

    for likelihood_path in likelihood_paths:
        logger.logger.info(likelihood_path.name)
        df_summary = make_eval(eval_datetime, likelihood_path)
        update_summary(df_summary)
        logger.logger.info('')


if __name__ == '__main__':
    set_logger()
    logger.logger.info('\nEvaluation started.\n')
    args = check_eval_options()
    main(args)
    logger.logger.info('\nUpdated summary.')
    logger.logger.info('Evaluation done.\n')
