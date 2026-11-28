int _fltused = 0;
__declspec(dllimport) double CreateEngine(double); __declspec(dllexport) double Process(double x) { return CreateEngine(x); }
