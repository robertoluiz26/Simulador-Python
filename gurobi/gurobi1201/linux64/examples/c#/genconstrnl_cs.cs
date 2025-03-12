/* Copyright 2025, Gurobi Optimization, LLC */

/* This example formulates and solves the following simple nonlinear model:

     minimize    y
     subject to  y = sin(2.5*x1) + x2
                 y free
                 -1 <= x1, x2 <= 1
*/

using System;
using Gurobi;

class mip1_cs
{
  static void Main()
  {
    /* Array representation of expression tree for sin(2.5 * x1) + x2 */
    int[] opcode = {GRB.OPCODE_PLUS, GRB.OPCODE_SIN, GRB.OPCODE_MULTIPLY,
                    GRB.OPCODE_CONSTANT, GRB.OPCODE_VARIABLE,
                    GRB.OPCODE_VARIABLE};
    double[] data = {-1.0, -1.0, -1.0, 2.5, -1.0, -1.0};
    int[] parent = {-1, 0, 1, 2, 2, 0};

    try {

      // Create environment
      GRBEnv env = new GRBEnv("genconstrnl.log");

      // Create empty model
      GRBModel model = new GRBModel(env);

      // Create variables, only y has an objective coefficient
      GRBVar y = model.AddVar(-GRB.INFINITY, GRB.INFINITY, 1.0, GRB.CONTINUOUS,
		              "y");
      GRBVar x1 = model.AddVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x1");
      GRBVar x2 = model.AddVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x2");

      // Finalize expression with variables indices
      data[4] = x1.Index;
      data[5] = x2.Index;

      // Add general nonlinear constraint y = sin(2.5*x1) + x2
      model.AddGenConstrNL(y, opcode, data, parent, "nonlinear_constr");

      // Optimize model
      model.Optimize();

      Console.WriteLine(y.VarName + " " + y.X);
      Console.WriteLine(x1.VarName + " " + x1.X);
      Console.WriteLine(x2.VarName + " " + x2.X);

      Console.WriteLine("Obj: " + model.ObjVal);

      // Dispose of model and env
      model.Dispose();
      env.Dispose();

    } catch (GRBException e) {
      Console.WriteLine("Error code: " + e.ErrorCode + ". " + e.Message);
    }
  }
}
