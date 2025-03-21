// Copyright (C) 2025, Gurobi Optimization, LLC
// All Rights Reserved
#ifndef _CPP_SOS_H_
#define _CPP_SOS_H_

class GRBSOSRep // private one
{
  private:
    GRBmodel*  Cmodel;
    int        num;
  public:
    friend class GRBSOS;
};

class GRBSOS
{
  private:

    GRBSOSRep* sosRep;

    GRBSOS (GRBmodel* xmodel, int sos);
    void setindex(int sos);
    int  getindex() const;
    void remove();

  public:

    friend class GRBModel;

    GRBSOS();
    GRBSOS(const GRBSOS& sos) : sosRep(sos.sosRep) {}

    GRBSOS& operator=(const GRBSOS& sos) { sosRep = sos.sosRep; return *this; }

    int get(GRB_IntAttr attr) const;

    void set(GRB_IntAttr attr, int value);
};
#endif
