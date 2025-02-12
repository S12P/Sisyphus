
#pragma ACCEL kernel

void kernel_atax(double A[390][410],double x[410],double y[410],double tmp[390])
{
  int i;
  int j;
{
    
    for (j = 0; j < 410; j++) {
      y[j] = 0.0;
    }

    for (i = 0; i < 390; i++) {
      tmp[i] = 0.0;
    }

    for (i = 0; i < 390; i++) {
      for (j = 0; j < 410; j++) {
      
        tmp[i] = tmp[i] + A[i][j] * x[j];
      }
    }
    for (j = 0; j < 410; j++) {
      for (i = 0; i < 390; i++) {
      
        y[j] = y[j] + A[i][j] * tmp[i];
      }
    }
  }
}
