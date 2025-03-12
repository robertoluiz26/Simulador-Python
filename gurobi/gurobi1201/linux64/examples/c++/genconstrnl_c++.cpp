/* Copyright 2025, Gurobi Optimization, LLC */

/* This example formulates and solves the following simple nonlinear model:

     minimize    y
     subject to  y = sin(2.5*x1) + x2
                 y free
                 -1 <= x1, x2 <= 1
*/

#include "gurobi_c++.h"
using namespace std;

int
main(int   argc,
     char *argv[])
{
  /* Array representation of expression tree for sin(2.5 * x1) + x2 */
  int     opcode[6] = {GRB_OPCODE_PLUS, GRB_OPCODE_SIN, GRB_OPCODE_MULTIPLY,
                       GRB_OPCODE_CONSTANT, GRB_OPCODE_VARIABLE,
                       GRB_OPCODE_VARIABLE};
  double  data[6]   = {-1.0, -1.0, -1.0, 2.5, -1.0, -1.0};
  int     parent[6] = {-1, 0, 1, 2, 2, 0};

  try {

    // Create an environment
    GRBEnv env = GRBEnv("genconstrnl.log");

    // Create an empty model
    GRBModel model = GRBModel(env);

    // Create variables, only y has an objective coefficient
    GRBVar y = model.addVar(-GRB_INFINITY, GRB_INFINITY, 1.0, GRB_CONTINUOUS,
                            "y");
    GRBVar x1 = model.addVar(-1.0, 1.0, 0.0, GRB_CONTINUOUS, "x1");
    GRBVar x2 = model.addVar(-1.0, 1.0, 0.0, GRB_CONTINUOUS, "x2");

    // Finalize expression with variables indices
    data[4] = x1.index();
    data[5] = x2.index();

    // Add general nonlinear constraint y = sin(2.5*x1) + x2
    model.addGenConstrNL(y, 6, opcode, data, parent);

    // Optimize model
    model.optimize();

    cout << y.get(GRB_StringAttr_VarName) << " "
         << y.get(GRB_DoubleAttr_X) << endl;
    cout << x1.get(GRB_StringAttr_VarName) << " "
         << x1.get(GRB_DoubleAttr_X) << endl;
    cout << x2.get(GRB_StringAttr_VarName) << " "
         << x2.get(GRB_DoubleAttr_X) << endl;

    cout << "Obj: " << model.get(GRB_DoubleAttr_ObjVal) << endl;

  } catch(GRBException e) {
    cout << "Error code = " << e.getErrorCode() << endl;
    cout << e.getMessage() << endl;
  } catch(...) {
    cout << "Exception during optimization" << endl;
  }

  return 0;
}
