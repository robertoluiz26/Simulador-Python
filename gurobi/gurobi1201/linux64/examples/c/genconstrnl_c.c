/* Copyright 2025, Gurobi Optimization, LLC */

/* This example formulates and solves the following simple nonlinear model:

     minimize    y
     subject to  y = sin(2.5*x1) + x2
                 y free
                 -1 <= x1, x2 <= 1
*/

#include <stdlib.h>
#include <stdio.h>
#include "gurobi_c.h"

int
main(int   argc,
     char *argv[])
{
  GRBenv   *env   = NULL;
  GRBmodel *model = NULL;
  int       error = 0;

  /* Data for optimization variables */
  double  lb[3]       = {-GRB_INFINITY, -1.0, -1.0};
  double  ub[3]       = {GRB_INFINITY, 1.0, 1.0};
  double  obj[3]      = {1.0, 0.0, 0.0};
  char   *varnames[3] = {"y", "x1", "x2"};

  /* Array representation of expression tree for sin(2.5 * x1) + x2 */
  int     opcode[6] = {GRB_OPCODE_PLUS, GRB_OPCODE_SIN, GRB_OPCODE_MULTIPLY,
                       GRB_OPCODE_CONSTANT, GRB_OPCODE_VARIABLE,
                       GRB_OPCODE_VARIABLE};
  double  data[6]   = {-1.0, -1.0, -1.0, 2.5, 1.0, 2.0};
  int     parent[6] = {-1, 0, 1, 2, 2, 0};

  /* Data for querying solution information */
  double    sol[3];
  int       optimstatus;
  double    objval;

  /* Create environment */
  error = GRBloadenv(&env, "genconstrnl.log");
  if (error) goto QUIT;

  /* Create model with the three optimization variables */
  error = GRBnewmodel(env, &model, "genconstrnl", 3, obj, lb, ub, NULL,
                      varnames);
  if (error) goto QUIT;

  /* Add general nonlinear constraint y = sin(2.5*x1) + x2 */
  error = GRBaddgenconstrNL(model, NULL, 0, 6, opcode, data, parent);
  if (error) goto QUIT;

  /* Optimize model */
  error = GRBoptimize(model);
  if (error) goto QUIT;

  /* Capture solution information */
  error = GRBgetintattr(model, GRB_INT_ATTR_STATUS, &optimstatus);
  if (error) goto QUIT;

  error = GRBgetdblattr(model, GRB_DBL_ATTR_OBJVAL, &objval);
  if (error) goto QUIT;

  error = GRBgetdblattrarray(model, GRB_DBL_ATTR_X, 0, 3, sol);
  if (error) goto QUIT;

  printf("\nOptimization complete\n");
  if (optimstatus == GRB_OPTIMAL) {
    printf("Optimal objective: %.4e\n", objval);

    printf("  y=%.6f, x1=%.6f, x2=%.6f\n", sol[0], sol[1], sol[2]);
  } else if (optimstatus == GRB_INF_OR_UNBD) {
    printf("Model is infeasible or unbounded\n");
  } else {
    printf("Optimization was stopped early\n");
  }

QUIT:

  /* Error reporting */
  if (error) {
    printf("ERROR: %s\n", GRBgeterrormsg(env));
    exit(1);
  }

  /* Free model */
  GRBfreemodel(model);

  /* Free environment */
  GRBfreeenv(env);

  return 0;
}
