/* Copyright 2025, Gurobi Optimization, LLC */

/* This example formulates and solves the following simple nonlinear model:

     minimize    y
     subject to  y = sin(2.5*x1) + x2
                 y free
                 -1 <= x1, x2 <= 1
*/

import com.gurobi.gurobi.*;

public class GenconstrNL {
    public static void main(String[] args) {

    /* Array representation of expression tree for sin(2.5 * x1) + x2 */
    int opcode[] = new int[] {GRB.OPCODE_PLUS, GRB.OPCODE_SIN, GRB.OPCODE_MULTIPLY,
                              GRB.OPCODE_CONSTANT, GRB.OPCODE_VARIABLE,
                              GRB.OPCODE_VARIABLE};
    double data[] = new double[] {-1.0, -1.0, -1.0, 2.5, -1.0, -1.0};
    int parent[] = new int[] {-1, 0, 1, 2, 2, 0};

    try {

      // Create environment
      GRBEnv env = new GRBEnv("genconstrnl.log");

      // Create empty model
      GRBModel model = new GRBModel(env);

      // Create variables, only y has an objective coefficient
      GRBVar y = model.addVar(-GRB.INFINITY, GRB.INFINITY, 1.0, GRB.CONTINUOUS,
                              "x");
      GRBVar x1 = model.addVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x1");
      GRBVar x2 = model.addVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x2");

      // Finalize expression with variables indices
      data[4] = x1.index();
      data[5] = x2.index();

      // Add general nonlinear constraint y = sin(2.5*x1) + x2
      model.addGenConstrNL(y, opcode, data, parent, "nonlinear_constr");

      // Optimize model
      model.optimize();

      System.out.println(y.get(GRB.StringAttr.VarName)
                         + " " +y.get(GRB.DoubleAttr.X));
      System.out.println(x1.get(GRB.StringAttr.VarName)
                         + " " +x1.get(GRB.DoubleAttr.X));
      System.out.println(x2.get(GRB.StringAttr.VarName)
                         + " " +x2.get(GRB.DoubleAttr.X));

      System.out.println("Obj: " + model.get(GRB.DoubleAttr.ObjVal));

      // Dispose of model and environment
      model.dispose();
      env.dispose();

    } catch (GRBException e) {
      System.out.println("Error code: " + e.getErrorCode() + ". " +
                         e.getMessage());
    }
  }
}
