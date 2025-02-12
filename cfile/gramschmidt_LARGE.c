#include <math.h>

#pragma ACCEL kernel

void kernel_gramschmidt(float A[1000][1200],float R[1200][1200],float Q[1000][1200])
{
  float nrm;
  int i;
  int j;
  int k;

{
    
    
    
    for (k = 0; k < 1200; k++) {
      nrm = 0.0;
      
      for (i = 0; i < 1000; i++) {
        nrm += A[i][k] * A[i][k];
      }
      R[k][k] = sqrt(nrm);
      
      for (i = 0; i < 1000; i++) {
        Q[i][k] = A[i][k] / R[k][k];
      }
      
      for (j = k + 1; j < 1200; j++) {
        R[k][j] = 0.0;
        
        for (i = 0; i < 1000; i++) {
          R[k][j] += Q[i][k] * A[i][j];
        }
        
        for (i = 0; i < 1000; i++) {
          A[i][j] = A[i][j] - Q[i][k] * R[k][j];
        }
      }
    }
  }
}
