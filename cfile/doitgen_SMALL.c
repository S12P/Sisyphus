
#pragma ACCEL kernel

void kernel_doitgen(float A[25][20][30],float C4[30][30],float sum[25][20][30])
{
  int r;
  int q;
  int p;
  int s;
{
    
    
    for (r = 0; r < 25; r++) {
      
      
      for (q = 0; q < 20; q++) {
        
        
        for (p = 0; p < 30; p++) {
          sum[r][q][p] = 0.0;
          for (s = 0; s < 30; s++) {
            sum[r][q][p] += A[r][q][s] * C4[s][p];
          }
        }
        for (p = 0; p < 30; p++) {
          A[r][q][p] = sum[r][q][p];
        }
      }
    }
  }
}
