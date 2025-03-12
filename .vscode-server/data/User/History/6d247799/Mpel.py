import gurobipy as gp

# Crie um modelo
model = gp.Model("teste")

# Adicione variáveis
x = model.addVar(name="x")
y = model.addVar(name="y")

# Adicione restrição
model.addConstr(x + y <= 10, "restricao")

# Defina a função objetivo
model.setObjective(x + y, sense=gp.GRB.MAXIMIZE)

# Resolva o modelo
model.optimize()

# Resultados
print(f"x = {x.X}, y = {y.X}")
print(f"Valor objetivo = {model.ObjVal}")