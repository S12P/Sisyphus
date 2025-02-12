


void kernel_gemm(float C[100][3072],float A[100][100],float B[100][3072])
{
    int i;
    int j;
    int k;
    
    for (i = 0; i < 100; i++) {
        
        for (j = 0; j < 3072; j++) {
            C[i][j] = 0;
            for (k = 0; k < 100; k++) {
                C[i][j] +=  A[i][k] * B[k][j];
            }
        }
    }
}

