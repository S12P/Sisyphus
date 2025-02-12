
#pragma ACCEL kernel

void kernel_doitgen(float A[150][140][160],float C4[160][160],float sum[150][140][160])
{
  int r;
  int q;
  int p;
  int s;
{
    
    
    
    for (r = 0; r < 150; r++) {
      
      
      
      for (q = 0; q < 140; q++) {
        
        
        
        for (p = 0; p < 160; p++) {
          sum[r][q][p] = 0.0;
          
          for (s = 0; s < 160; s++) {
            sum[r][q][p] += A[r][q][s] * C4[s][p];
          }
        }
        
        for (p = 0; p < 160; p++) {
          A[r][q][p] = sum[r][q][p];
        }
      }
    }
  }
}
