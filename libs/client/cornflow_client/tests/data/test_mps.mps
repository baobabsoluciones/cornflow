*SENSE:Minimize
NAME          test_export_dict_MIP
ROWS
 N  obj
 L  c1
 G  c2
 E  c3
COLUMNS
    x         c1         1.000000000000e+00
    x         c2         1.000000000000e+00
    x         obj        1.000000000000e+00
    y         c1         1.000000000000e+00
    y         c3        -1.000000000000e+00
    y         obj        4.000000000000e+00
    MARK      'MARKER'                 'INTORG'
    z         c2         1.000000000000e+00
    z         c3         1.000000000000e+00
    z         obj        9.000000000000e+00
    MARK      'MARKER'                 'INTEND'
RHS
    RHS       c1         5.000000000000e+00
    RHS       c2         1.000000000000e+01
    RHS       c3         7.500000000000e+00
BOUNDS
 UP BND       x          4.000000000000e+00
 LO BND       y         -1.000000000000e+00
 UP BND       y          1.000000000000e+00
 LO BND       z          0.000000000000e+00
ENDATA
