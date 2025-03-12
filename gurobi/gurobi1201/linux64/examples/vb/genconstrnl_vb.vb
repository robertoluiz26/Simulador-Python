' Copyright 2025, Gurobi Optimization, LLC
'
' This example formulates and solves the following simple nonlinear model:
'
'    minimize    y
'    subject to  y = sin(2.5*x1) + x2
'                y free
'                -1 <= x1, x2 <= 1


Imports System
Imports Gurobi

Class mip1_vb
    Shared Sub Main()
        ' Array representation of expression tree for sin(2.5 * x1) + x2
        Dim opcode As Integer() = new Integer() {GRB.OPCODE_PLUS,
            GRB.OPCODE_SIN, GRB.OPCODE_MULTIPLY, GRB.OPCODE_CONSTANT,
	    GRB.OPCODE_VARIABLE, GRB.OPCODE_VARIABLE}
        Dim data As Double() = new Double() {-1.0, -1.0, -1.0, 2.5, -1.0, -1.0}
        Dim parent As Integer() = new Integer() {-1, 0, 1, 2, 2, 0}

        Try
            Dim env As GRBEnv = New GRBEnv("genconstrnl.log")
            Dim model As GRBModel = New GRBModel(env)

            ' Create variables, only y has an objective coefficient
            Dim y As GRBVar = model.AddVar(-GRB.INFINITY, GRB.INFINITY, 1.0,
	        GRB.CONTINUOUS, "y")
            Dim x1 As GRBVar = model.AddVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x1")
            Dim x2 As GRBVar = model.AddVar(-1.0, 1.0, 0.0, GRB.CONTINUOUS, "x2")

            ' Finalize expression with variables indices
            data(4) = x1.Index
            data(5) = x2.Index

            ' Add general nonlinear constraint y = sin(2.5*x1) + x2
            model.AddGenConstrNL(y, opcode, data, parent, "nonlinear_constr")

            ' Optimize model

            model.Optimize()

            Console.WriteLine(y.VarName & " " & y.X)
            Console.WriteLine(x1.VarName & " " & x1.X)
            Console.WriteLine(x2.VarName & " " & x2.X)

            Console.WriteLine("Obj: " & model.ObjVal)

            ' Dispose of model and env

            model.Dispose()
            env.Dispose()

        Catch e As GRBException
            Console.WriteLine("Error code: " & e.ErrorCode & ". " & e.Message)
        End Try
    End Sub
End Class
