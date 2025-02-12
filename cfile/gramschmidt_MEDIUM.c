#include <math.h>

#pragma ACCEL kernel

void kernel_gramschmidt(float A[200][240],float R[240][240],float Q[200][240])
{
  float nrm[240];
  int i;
  int j;
  int k;
  
{
    
    
    
    for (k = 0; k < 240; k++) {
      nrm[k] = 0.0;
      
      for (i = 0; i < 200; i++) {
        nrm[k] += A[i][k] * A[i][k];
      }
      R[k][k] = sqrt(nrm[k]);
      
      for (i = 0; i < 200; i++) {
        Q[i][k] = A[i][k] / R[k][k];
      }
      
      for (j = k + 1; j < 240; j++) {
        R[k][j] = 0.0;
        
        for (i = 0; i < 200; i++) {
          R[k][j] += Q[i][k] * A[i][j];
        }
        
        for (i = 0; i < 200; i++) {
          A[i][j] = A[i][j] - Q[i][k] * R[k][j];
        }
      }
    }
  }
}
