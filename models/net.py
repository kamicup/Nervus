#!/usr/bin/env python
# -*- coding: utf-8 -*-r

from collections import OrderedDict
import torch.nn as nn
import torchvision.models as models
from torchvision.ops import MLP


class BaseNet:
    cnn = {
            'ResNet18': models.resnet18,
            'ResNet': models.resnet50,
            'DenseNet': models.densenet161,
            'B0': models.efficientnet_b0,
            'B2': models.efficientnet_b2,
            'B4': models.efficientnet_b4,
            'B6': models.efficientnet_b6,
            'ConvNeXtTiny': models.convnext_tiny,
            'ConvNeXtSmall': models.convnext_small,
            'ConvNeXtBase': models.convnext_base,
            'ConvNeXtLarge': models.convnext_large
        }

    vit = {
            'ViTb16': models.vit_b_16,
            'ViTb32': models.vit_b_32,
            'ViTl16': models.vit_l_16,
            'ViTl32': models.vit_l_32
        }

    vit_weight = {
                    'ViTb16': models.ViT_B_16_Weights.DEFAULT,
                    'ViTb32': models.ViT_B_32_Weights.DEFAULT,
                    'ViTl16': models.ViT_L_16_Weights.DEFAULT,
                    'ViTl32': models.ViT_L_32_Weights.DEFAULT
                }

    net = {**cnn, **vit}

    classifier = {
                'ResNet18': 'fc',
                'ResNet': 'fc',
                'DenseNet': 'classifier',
                'B0': 'classifier',
                'B2': 'classifier',
                'B4': 'classifier',
                'B6': 'classifier',
                'ConvNeXtTiny': 'classifier',
                'ConvNeXtSmall': 'classifier',
                'ConvNeXtBase': 'classifier',
                'ConvNeXtLarge': 'classifier',
                'ViTb16': 'heads',
                'ViTb32': 'heads',
                'ViTl16': 'heads',
                'ViTl32': 'heads'
                }

    mlp_config = {
                'hidden_channels': [256, 256, 256],
                'dropout': 0.2
                }

    @classmethod
    def MLPNet(cls, num_inputs):
        mlp = MLP(in_channels=num_inputs, hidden_channels=cls.mlp_config['hidden_channels'], dropout=cls.mlp_config['dropout'])
        return mlp

    @classmethod
    def set_net(cls, net_name, vit_image_size=None):
        if net_name in cls.cnn:
            net = cls.cnn[net_name]()
        else:
            assert isinstance(vit_image_size, int), f"Invalid image size for ViT: {vit_image_size}."
            net = cls.set_vit(cls, net_name, vit_image_size)
        return net

    @classmethod
    def set_vit(cls, net_name, vit_image_size):
        base_vit = cls.vit[net_name]
        pretrained_vit = base_vit(pretrained=cls.vit_weight[net_name])

        if vit_image_size == 224:
            return pretrained_vit  # Default
        else:
            # Modify shape of weight
            weight = pretrained_vit.state_dict()
            patch_size = int(net_name[-2:])  # 'ViTb16' -> 16
            aligned_weight = models.vision_transformer.interpolate_embeddings(
                                                        image_size=vit_image_size,
                                                        patch_size=patch_size,
                                                        model_state=weight
                                                        )
            aligned_vit = base_vit(image_size=vit_image_size)
            aligned_vit.load_state_dict(aligned_weight)
            return aligned_vit

    @classmethod
    def constuct_extractor(cls, net_name, mlp_num_inputs=None, vit_image_size=None):
        if net_name == 'MLP':
            assert isinstance(mlp_num_inputs, int), f"Invalid number of inputs for MLP: {mlp_num_inputs}."
            extractor = cls.MLPNet(mlp_num_inputs)
        else:
            assert net_name in cls.net, f"No specified net: {net_name}."
            DUMMY_CLASSIFIER = nn.Identity()
            extractor = cls.set_net(net_name, vit_image_size)
            extractor._modules[cls.classifier[net_name]] = DUMMY_CLASSIFIER
        return extractor

    @classmethod
    def get_classifier(cls, net_name):
        net = cls.net[net_name]()
        classifier = net._modules[cls.classifier[net_name]]
        return classifier

    @classmethod
    def construct_multi_classifier(cls, net_name, num_classes_in_internal_label):
        classifiers = dict()

        if net_name == 'MLP':
            in_features = cls.mlp_config['hidden_channels'][-1]
            for internal_label_name, num_classes in num_classes_in_internal_label.items():
                classifiers[internal_label_name] = nn.Linear(in_features, num_classes)

        elif net_name.startswith('ResNet') or net_name.startswith('DenseNet'):
            base_classifier = cls.get_classifier(net_name)
            in_features = base_classifier.in_features
            for internal_label_name, num_classes in num_classes_in_internal_label.items():
                classifiers[internal_label_name] = nn.Linear(in_features, num_classes)

        elif net_name.startswith('B'):
            base_classifier = cls.get_classifier(net_name)
            dropout = base_classifier[0].p
            in_features = base_classifier[1].in_features
            for internal_label_name, num_classes in num_classes_in_internal_label.items():
                classifiers[internal_label_name] = nn.Sequential(
                                                    nn.Dropout(p=dropout, inplace=False),
                                                    nn.Linear(in_features, num_classes)
                                                    )

        elif net_name.startswith('ConvNeXt'):
            base_classifier = cls.get_classifier(net_name)
            layer_norm = base_classifier[0]
            flatten = base_classifier[1]
            in_features = base_classifier[2].in_features
            for internal_label_name, num_classes in num_classes_in_internal_label.items():
                classifiers[internal_label_name] = nn.Sequential(
                                                    layer_norm,
                                                    flatten,
                                                    nn.Linear(in_features, num_classes)
                                                    )
        else:
            # ViT
            # x = self.encoder(x)
            # Classifier "token" as used by standard language architectures
            # x = x[:, 0]
            base_classifier = cls.get_classifier(net_name)
            in_features = base_classifier.head.in_features
            for internal_label_name, num_classes in num_classes_in_internal_label.items():
                classifiers[internal_label_name] = nn.Sequential(OrderedDict([
                                                        ('head', nn.Linear(in_features, num_classes))
                                                    ]))

        multi_classifier = nn.ModuleDict(classifiers)
        return multi_classifier
