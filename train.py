#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import torch
from lib import (
        check_train_options,
        create_model,
        set_logger
        )
from lib import Logger as logger


def main(opt):
    model = create_model(opt.args)
    model.print_parameter()
    model.print_dataset_info()

    for epoch in range(model.epochs):
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            elif phase == 'val':
                model.eval()
            else:
                raise ValueError(f"Invalid phase: {phase}.")

            split_dataloader = model.dataloaders[phase]
            dataset_size = len(split_dataloader.dataset)

            for i, data in enumerate(split_dataloader):
                model.optimizer.zero_grad()
                model.set_data(data)

                with torch.set_grad_enabled(phase == 'train'):
                    model.forward()
                    model.cal_batch_loss()

                    if phase == 'train':
                        model.backward()
                        model.optimize_parameters()

                model.cal_running_loss(batch_size=len(data['imgpath']))

            model.cal_epoch_loss(epoch, phase, dataset_size=dataset_size)

        model.print_epoch_loss(epoch)

        if model.is_total_val_loss_updated():
            model.store_weight()
            if (epoch > 0) and (model.save_weight_policy == 'each'):
                model.save_weight(as_best=False)

    model.save_learning_curve()
    model.save_weight(as_best=True)
    model.save_parameter()


if __name__ == '__main__':
    set_logger()
    datetime_name = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    logger.logger.info(f"\nTraining started at {datetime_name}.\n")

    opt = check_train_options(datetime_name)
    main(opt)

    logger.logger.info('\nTraining finished.\n')
