from __future__ import print_function
import argparse
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.utils.data
from torch.autograd import Variable
import skimage
import skimage.io
import skimage.transform
import numpy as np
import time
import preprocess
import sys
sys.path.append('..')
from models import *
import cv2
import matplotlib.pyplot as plt


def test(imgL,imgR):
    '''use convolution model to compute the disparity distribution'''

    model.eval()

    if args.cuda:
       imgL = torch.FloatTensor(imgL).cuda()
       imgR = torch.FloatTensor(imgR).cuda()

    imgL, imgR= Variable(imgL), Variable(imgR)

    with torch.no_grad():
        disp = model(imgL,imgR)

    disp = torch.squeeze(disp)
    pred_disp = disp.data.cpu().numpy()

    return pred_disp


def main(ileft, iright):
    '''image preprocess and generate disparity info'''
    processed = preprocess.get_transform(augment=False)
    if ileft and iright:
       args.leftimg = ileft
       args.rightimg = iright
    if args.isgray:
       imgL_o = cv2.cvtColor(cv2.imread(args.leftimg,0), cv2.COLOR_GRAY2RGB)
       imgR_o = cv2.cvtColor(cv2.imread(args.rightimg,0), cv2.COLOR_GRAY2RGB)
    else:
       imgL_o = (skimage.io.imread(args.leftimg).astype('float32'))
       imgR_o = (skimage.io.imread(args.rightimg).astype('float32'))

    imgL = processed(imgL_o).numpy()
    imgR = processed(imgR_o).numpy()
    imgL = np.reshape(imgL,[1,3,imgL.shape[1],imgL.shape[2]])
    imgR = np.reshape(imgR,[1,3,imgR.shape[1],imgR.shape[2]])

    # pad to width and hight to 16 times
    if imgL.shape[2] % 16 != 0:
        times = imgL.shape[2]//16
        top_pad = (times+1)*16 -imgL.shape[2]
    else:
        top_pad = 0
    if imgL.shape[3] % 16 != 0:
        times = imgL.shape[3]//16
        left_pad = (times+1)*16-imgL.shape[3]
    else:
        left_pad = 0
    imgL = np.lib.pad(imgL,((0,0),(0,0),(top_pad,0),(0,left_pad)),mode='constant',constant_values=0)
    imgR = np.lib.pad(imgR,((0,0),(0,0),(top_pad,0),(0,left_pad)),mode='constant',constant_values=0)

    start_time = time.time()
    pred_disp = test(imgL,imgR)
    print('time = %.2f' %(time.time() - start_time))
    if top_pad !=0 or left_pad != 0:
        img = pred_disp[top_pad:,:-left_pad]
    else:
        img = pred_disp


    return img


parser = argparse.ArgumentParser(description='PSMNet')
parser.add_argument('--KITTI', default='2015',
                    help='KITTI version')
parser.add_argument('--datapath', default=None,
                    help='select model')
parser.add_argument('--loadmodel', default='../trained/KITTI2015.tar',
                    help='loading model')
parser.add_argument('--leftimg', default=None,
                    help='load model')
parser.add_argument('--rightimg', default=None,
                    help='load model')
parser.add_argument('--isgray', default=False,
                    help='load model')
parser.add_argument('--model', default='stackhourglass',
                    help='select model')
parser.add_argument('--maxdisp', type=int, default=192,
                    help='maxium disparity')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)

if args.model == 'stackhourglass':
    model = stackhourglass(args.maxdisp)
elif args.model == 'basic':
    model = basic(args.maxdisp)
else:
    print('no model')

model = nn.DataParallel(model, device_ids=[0])
model.cuda()

if args.loadmodel is not None:
    print('load SDENet')
    state_dict = torch.load(args.loadmodel)
    model.load_state_dict(state_dict['state_dict'])

print('Number of model parameters: {}'.format(sum([p.data.nelement() for p in model.parameters()])))

if __name__ == '__main__':
    main()
