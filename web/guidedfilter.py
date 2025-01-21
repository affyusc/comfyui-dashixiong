import torch
import torch.nn.functional as F

class GuidedFilter:
    def __init__(self, r, eps=1e-8):
        self.r = r
        self.eps = eps

    def _box_filter(self, x, r):
        ch = x.shape[1]
        k = 2 * r + 1
        weight = torch.ones(ch, 1, k, k, device=x.device) / (k * k)
        return F.conv2d(x, weight, padding=r, groups=ch)

    def filter(self, x, y):
        x = x.float()
        y = y.float()
        
        N = self._box_filter(torch.ones_like(x), self.r)
        mean_x = self._box_filter(x, self.r) / N
        mean_y = self._box_filter(y, self.r) / N
        cov_xy = self._box_filter(x * y, self.r) / N - mean_x * mean_y
        var_x = self._box_filter(x * x, self.r) / N - mean_x * mean_x
        
        A = cov_xy / (var_x + self.eps)
        b = mean_y - A * mean_x
        
        mean_A = self._box_filter(A, self.r) / N
        mean_b = self._box_filter(b, self.r) / N
        
        output = mean_A * x + mean_b
        return output