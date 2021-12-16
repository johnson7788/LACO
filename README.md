#Enhancing Label Correlation Feedback in Multi-Label Text Classification via Multi-Task Learning
This repository contains the code for the ACL 2021 paper
>["Enhancing Label Correlation Feedback in Multi-Label Text Classification via Multi-Task Learning"](https://arxiv.org/abs/2106.03103).

If you use LACO in your work, please cite it as follows:
``` bibtex
@article{zhang2021enhancing,
  title={Enhancing Label Correlation Feedback in Multi-Label Text Classification via Multi-Task Learning},
  author={Zhang, Ximing and Zhang, Qian-Wen and Yan, Zhao and Liu, Ruifang and Cao, Yunbo},
  journal={arXiv preprint arXiv:2106.03103},
  year={2021}
}
```
##Settings
环境设置

- python 3.6+

- Tensorflow 1.12.0+

环境准备

- 你可以在以下内容中改变实验设置 LACO/common/global_config.py

- 目录LACO/ie/src/bert下的初始内容主要来自[Google bert](https://github.com/google-research/bert)。引用信息被记录在相应的文件中。你可以在LACO/pretrained_model/下载并解压。

##数据集
- [AAPD](https://git.uwaterloo.ca/jimmylin/Castor-data/tree/master/datasets/AAPD)
- [RCV1-V2](http://www.ai.mit.edu/projects/jmlr/papers/volume5/lewis04a/lyrl2004_rcv1v2_README.htm)

数据准备

示例数据在LACO/log/re_model/input目录下。
请注意，"text "字段存储文本内容，"spo_list "字段存储 "predicate "中的相关标签，其他字段可以忽略不计。

``` bibtex
{
  "text": "the alignment of a set of objects by means of transformations plays an important role in computer vision whilst the case for only two objects can be solved globally , when multiple objects are considered usually iterative methods are used in practice the iterative methods perform well if the relative transformations between any pair of objects are free of noise however , if only noisy relative transformations are available \\( e g due to missing data or wrong correspondences \\) the iterative methods may fail based on the observation that the underlying noise free transformations can be retrieved from the null space of a matrix that can directly be obtained from pairwise alignments , this paper presents a novel method for the synchronisation of pairwise transformations such that they are transitively consistent simulations demonstrate that for noisy transformations , a large proportion of missing data and even for wrong correspondence assignments the method delivers encouraging results\n",
  "spo_list": [
    {
      "predicate": "label4",
      "subject": "sub",
      "object": {
        "@value": "obj"
      },
      "object_type": {
        "@value": "Text"
      }
    },
    {
      "predicate": "label14",
      "subject": "sub",
      "object": {
        "@value": "obj"
      },
      "object_type": {
        "@value": "Text"
      }
    }
  ],
  "subject": "",
  "details_info": {},
  "auto_id": 0
}
```

##怎样运行
-  Train_mltc_with_plcp:    python ie/train_main_plcp.py
-  Test_mltc_with_plcp:     python ie/test_main_plcp.py
-  Train_mltc_with_clcp:    python ie/train_main_clcp.py
-  Test_mltc_with_clcp:     python ie/test_main_clcp.py

##Results
The best model of +PLCP of AAPD dataset and and RCV1V2 dataset can be found at https://share.weiyun.com/5EXHqEPE (password: 8yrgji) for your reference.

##© Copyright
	Ximing Zhang (ximingzhang@bupt.edu.cn),
	Qian-Wen Zhang (cowenzhang@tencent.com),
	Zhao Yan (zhaoyan@tencent.com),
	Ruifang Liu (lrf@bupt.edu.cn),
	Yunbo Cao (yunbocao@tencent.com),
	Tencent Cloud Xiaowei, Beijing, China  && Beijing University of Posts and Telecommunications, Beijing, China  

This code package can be used freely for academic, non-profit purposes. For other usage, 
please contact us for further information (Ximing Zhang: ximingzhang@bupt.edu.cn).