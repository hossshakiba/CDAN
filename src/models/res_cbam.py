import torch
import torch.nn as nn
import torch.nn.functional as F

import cv2

from models.cbam import CBAM
from models.res_bam import BAM
from models.NLNN import NLBlockND


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ConvBlock, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=1, padding=1)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        out = self.conv(x)
        out = self.bn(out)
        out = self.relu(out)
        return out
    

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv = nn.Conv2d(channels, channels, kernel_size=3, stride=1, padding=1)
        self.bn = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.BAM = BAM(channels)

    def forward(self, x):
        residual = x
        out = self.conv(x)
        out = self.bn(x)
        out = self.relu(out)
        out = self.conv(out)
        out = self.bn(x)
        out += residual
        # out = self.BAM(out)
        out = self.relu(out)
        return out


class LLIE(nn.Module):
    def __init__(self):
        super(LLIE, self).__init__()
        self.encoder_conv1 = ConvBlock(3, 64)
        self.encoder_residual1 = ResidualBlock(64)
        self.encoder_maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder_nlnet1 = NLBlockND(64)
        self.encoder_conv2 = ConvBlock(64, 128)
        self.encoder_residual2 = ResidualBlock(128)
        self.encoder_maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder_nlnet2 = NLBlockND(128)
        self.encoder_conv3 = ConvBlock(128, 256)
        self.encoder_residual3 = ResidualBlock(256)
        self.encoder_maxpool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder_nlnet3 = NLBlockND(256)
        self.encoder_conv4 = ConvBlock(256, 512)
        self.encoder_residual4 = ResidualBlock(512)
        self.encoder_nlnet4 = NLBlockND(512)

        self.bottleneck = CBAM(512)

        self.decoder_convt1 = nn.ConvTranspose2d(512, 256, kernel_size=3, stride=1, padding=1)
        self.decoder_conv1 = ConvBlock(256, 256)
        self.decoder_cbam1 = CBAM(256)
        self.decoder_bn1 = nn.BatchNorm2d(256)
        self.decoder_convt2 = nn.ConvTranspose2d(256, 128, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.decoder_conv2 = ConvBlock(128, 128)
        self.decoder_cbam2 = CBAM(128)
        self.decoder_bn2 = nn.BatchNorm2d(128)
        self.decoder_convt3 = nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.decoder_conv3 = ConvBlock(64, 64)
        self.decoder_cbam3 = CBAM(64)
        self.decoder_bn3 = nn.BatchNorm2d(64)
        self.decoder_convt4 = nn.ConvTranspose2d(64, 3, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.decoder_nlnet4 = NLBlockND(3)
        self.decoder_conv4 = ConvBlock(3, 3)
        self.decoder_bn4 = nn.BatchNorm2d(3)
        self.decoder_relu = nn.ReLU(inplace=True)
        self.decoder_sigmoid = nn.Sigmoid()

    def forward(self, x):
        skip_connections = []
        # Encoder
        out = self.encoder_conv1(x)
        out = self.encoder_residual1(out)
        out = self.encoder_maxpool1(out)
        # out = self.encoder_nlnet1(out)
        skip_connections.append(out)
        out = self.encoder_conv2(out)
        out = self.encoder_residual2(out)
        out = self.encoder_maxpool2(out)
        # out = self.encoder_nlnet2(out)
        skip_connections.append(out)
        out = self.encoder_conv3(out)
        out = self.encoder_residual3(out)
        out = self.encoder_maxpool3(out)
        # out = self.encoder_nlnet3(out)
        skip_connections.append(out)
        out = self.encoder_conv4(out)
        out = self.encoder_residual4(out)
        # out = self.encoder_nlnet4(out)
        skip_connections.append(out)
        # Bottleneck
        out = self.bottleneck(out)
        out = self.encoder_nlnet4(out)

        # Decoder
        out = torch.add(out, skip_connections[3])
        out = self.decoder_convt1(out)
        # out = self.decoder_conv1(out)
        out = self.decoder_bn1(out)
        out = self.decoder_relu(out)
        out = torch.add(out, skip_connections[2])
        # out = self.decoder_cbam1(out)
        out = self.decoder_convt2(out)
        # out = self.decoder_conv2(out)
        out = self.decoder_bn2(out)
        out = self.decoder_relu(out)
        out = torch.add(out, skip_connections[1])
        # out = self.decoder_cbam2(out)
        out = self.decoder_convt3(out)
        # out = self.decoder_conv3(out)
        out = self.decoder_bn3(out)
        out = self.decoder_relu(out)
        out = torch.add(out, skip_connections[0])
        # out = self.decoder_cbam3(out)
        out = self.decoder_convt4(out)
        # out = self.decoder_conv4(out)
        out = self.decoder_bn4(out)
        # out = self.decoder_nlnet4(out)
        out = self.decoder_sigmoid(out)

        return out
