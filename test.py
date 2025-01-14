#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import torch
from lib import (
        check_test_options,
        create_model,
        set_logger
        )
from lib import Logger as logger
from typing import List


def _collect_weight(weight_dir: str) -> List[Path]:
    """
    Return list of weight paths.

    Args:
        weight_dir (st): path to directory of weights

    Returns:
        List[Path]: list of weight paths
    """
    weight_paths = list(Path(weight_dir).glob('*.pt'))
    assert weight_paths != [], f"No weight in {weight_dir}."
    weight_paths.sort(key=lambda path: path.stat().st_mtime)
    return weight_paths


def main(opt):
    model = create_model(opt.args)
    model.print_parameter()
    model.print_dataset_info()

    weight_paths = _collect_weight(model.weight_dir)
    for weight_path in weight_paths:
        logger.logger.info(f"Inference with {weight_path.name}.")

        # weight is reset by overwriting every time.
        model.load_weight(weight_path)
        model.eval()

        for split in model.test_splits:
            split_dataloader = model.dataloaders[split]

            for i, data in enumerate(split_dataloader):
                model.set_data(data)

                with torch.no_grad():
                    model.forward()
                    model.make_likelihood(data)

        model.save_likelihood(weight_path.stem)


if __name__ == '__main__':
    set_logger()
    logger.logger.info('\nTest started.\n')

    opt = check_test_options()
    main(opt)

    logger.logger.info('\nTest finished.\n')
