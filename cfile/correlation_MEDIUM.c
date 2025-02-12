#include <math.h>

#pragma ACCEL kernel

void kernel_correlation(float var,float data[260][240],float corr[240][240],float mean[240],float stddev[240])
{
  float eps = 0.1;
  int i;
  int j;
  int k;

{
    
    
    
    for (j = 0; j < 240; j++) {
      mean[j] = 0.0;
      
      for (i = 0; i < 260; i++) {
        mean[j] += data[i][j];
      }
      mean[j] /= var;
    }
    
    
    
    for (j = 0; j < 240; j++) {
      stddev[j] = 0.0;
      
      for (i = 0; i < 260; i++) {
        stddev[j] += (data[i][j] - mean[j]) * (data[i][j] - mean[j]);
      }
      stddev[j] /= var;
      stddev[j] = sqrt(stddev[j]);
/* The following in an inelegant but usual way to handle
			   near-zero std. dev. values, which below would cause a zero-
			   divide. */
      stddev[j] = (stddev[j] <= eps?1.0 : stddev[j]);
    }
    
    
    
    for (i = 0; i < 260; i++) {
      
      for (j = 0; j < 240; j++) {
        data[i][j] -= mean[j];
        data[i][j] /= sqrt(var) * stddev[j];
      }
    }
    
    
    
    for (i = 0; i < 240 - 1; i++) {
      corr[i][i] = 1.0;
      
      for (j = i + 1; j < 240; j++) {
        corr[i][j] = 0.0;
        
        for (k = 0; k < 260; k++) {
          corr[i][j] += data[k][i] * data[k][j];
        }
        corr[j][i] = corr[i][j];
      }
    }
    corr[240 - 1][240 - 1] = 1.0;
  }
}
