
#pragma ACCEL kernel

void kernel_bicg(double A[410][390],double s[390],double q[410],double p[390],double r[410])
{
  int i;
  int j;
{
    
    for (i = 0; i < 390; i++) {
      s[i] = 0.0;
    }
    
    
    
    for (i = 0; i < 410; i++) {
      q[i] = 0.0;
    }

    for (j = 0; j < 390; j++) {
      for (i = 0; i < 410; i++) {
      
        s[j] = s[j] + r[i] * A[i][j];
      }
    }
    for (i = 0; i < 410; i++) {
      for (j = 0; j < 390; j++) {
        q[i] = q[i] + A[i][j] * p[j];
      }
    }
  }
}
