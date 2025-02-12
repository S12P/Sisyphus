

void l16_two_conv(
  int8_t inp0[1][256][8][8],
  int8_t out0[1][256][8][8],
  int8_t weight0[256][256][3][3],

  int8_t inp1[1][128][16][16],
  int8_t out1[1][256][8][8],
  int8_t weight1[256][128][1][1]
) {	// L3089
  int8_t padding[1][256][10][10];	// L3090
  #pragma HLS STREAM variable=padding depth=12 type=fifo

  #pragma HLS dataflow

  for (int b = 0; b < 1; b++) {        // L4
    for (int c = 0; c < 256; c++) {        // L5
      for (int h = 0; h < 10; h++) {       // L6
        for (int w = 0; w < 10; w++) {     // L7
          int8_t v;     // L10
          v = 0;        // L11
          if (h >= 1 && h < 9 && w >= 1 && w < 9) {    // L35
            int8_t v11 = inp0[b][c][(h - 1)][(w - 1)];    // L36
            v = v11;    // L37
          }
          int8_t v12 = v;       // L39
          padding[b][c][h][w] = v12; // L40
        }
      }
    }
  }

  int8_t S_b_co_ho_wo_0_reuse_2[8][3][10];    // L7
  #pragma HLS array_partition variable=S_b_co_ho_wo_0_reuse_2 complete dim=1

  int8_t S_b_co_ho_wo_0_reuse_3[8][3][3];     // L8
  #pragma HLS array_partition variable=S_b_co_ho_wo_0_reuse_3 complete dim=1
  #pragma HLS array_partition variable=S_b_co_ho_wo_0_reuse_3 complete dim=2
  #pragma HLS array_partition variable=S_b_co_ho_wo_0_reuse_3 complete dim=3

  for (int b = 0; b < 1; b++) {     // L9
    for (int co = 0; co < 256; co++) {    // L10
      for (int ho = 0; ho < 10; ho++) {   // L11
        for (int wo = 0; wo < 10; wo++) { // L12

          int8_t temp = 0;
          for (int v9o = 0; v9o < 64; v9o++) {
            #pragma HLS pipeline II=1
            for (int v9 = 0; v9 < 8; v9++) {    // L13
              int8_t v10 = S_b_co_ho_wo_0_reuse_2[v9][1][wo];     // L14
              S_b_co_ho_wo_0_reuse_2[v9][0][wo] = v10;    // L15
              int8_t v11 = S_b_co_ho_wo_0_reuse_2[v9][2][wo];     // L16
              S_b_co_ho_wo_0_reuse_2[v9][1][wo] = v11;    // L17
              int8_t v12 = padding[b][v9][ho][wo];     // L18
              S_b_co_ho_wo_0_reuse_2[v9][2][wo] = v12;    // L19
            }
            if ((ho - 2) >= 0) {  // L21
              for (int v13 = 0; v13 < 8; v13++) {       // L22
                for (int v14 = 0; v14 < 3; v14++) {       // L23
                  int8_t v15 = S_b_co_ho_wo_0_reuse_3[v13][v14][1];       // L24
                  S_b_co_ho_wo_0_reuse_3[v13][v14][0] = v15;      // L25
                  int8_t v16 = S_b_co_ho_wo_0_reuse_3[v13][v14][2];       // L26
                  S_b_co_ho_wo_0_reuse_3[v13][v14][1] = v16;      // L27
                  int8_t v17 = S_b_co_ho_wo_0_reuse_2[v13][v14][wo];      // L28
                  S_b_co_ho_wo_0_reuse_3[v13][v14][2] = v17;      // L29
                }
              }
              if ((wo - 2) >= 0) {        // L32
                int8_t v; // L35
                v = 0;    // L36
                for (int ci = 0; ci < 8; ci++) {       // L37
                  for (int r = 0; r < 3; r++) {      // L38
                    for (int c = 0; c < 3; c++) {    // L39
                      int8_t v22 = S_b_co_ho_wo_0_reuse_3[ci][r][c];      // L40
                      int8_t v23 = weight0[co][ci][r][c];      // L41
                      int16_t v24 = v22;  // L42
                      int16_t v25 = v23;  // L43
                      int16_t v26 = v24 * v25;    // L44
                      int8_t v27 = v26;   // L45
                      int8_t v28 = v;     // L46
                      int8_t v29 = v28 + v27;     // L47
                      v = v29;    // L48
                    }
                  }
                }
                int8_t v30 = v;   // L52
                out0[b][co][(ho - 2)][(wo - 2)] = v30;      // L53
              }
            }
          }
          if ((ho - 2) >= 0 && (wo - 2) >= 0) {
            out0[b][co][(ho - 2)][(wo - 2)] = temp;
          }

        }
      }
    }
  }


  for (int b = 0; b < 1; b++) {     // L4
    for (int co = 0; co < 256; co++) {    // L5
      for (int ho = 0; ho < 8; ho++) {    // L6
        for (int wo = 0; wo < 8; wo++) {  // L7
          int8_t v;     // L10
          v = 0;        // L11
          for (int ci = 0; ci < 128; ci++) {   // L12
            for (int r = 0; r < 1; r++) {  // L13
              for (int c = 0; c < 1; c++) {        // L14
                int8_t v11 = inp1[b][ci][((ho * 2) + r)][((wo * 2) + c)]; // L15
                int8_t v12 = weight1[co][ci][r][c];  // L16
                int16_t v13 = v11;      // L17
                int16_t v14 = v12;      // L18
                int16_t v15 = v13 * v14;        // L19
                int8_t v16 = v15;       // L20
                int8_t v17 = v; // L21
                int8_t v18 = v17 + v16; // L22
                v = v18;        // L23
              }
            }
          }
          int8_t v19 = v;       // L27
          out1[b][co][ho][wo] = v19;      // L28
        }
      }
    }
  }

}

