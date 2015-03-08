# -*- coding: utf-8 -*-
from . import Project

__all__ = ["BaseProjectManager", "ProjectManager"]


class BaseProjectManager():
    pass


class ProjectManager():
    MAIN_PROJECT_CLASS = Project
    PROJECT_CLASS = Project
    
    def __init__(self, wf):
        self.wf = wf
        self.main = None
        self.sub = []
    
    def clear(self):
        self.main = None
        self.sub[:] = []
    
    def init(self, main_ptree, auxiliary_ptrees):
        self.main = self.build_main_project(main_ptree)
        
        for ptree in auxiliary_ptrees:
            project = self.build_project(ptree)
            self.sub.append(project)
        
        return self.main
    
    def __iter__(self):
        yield self.main
        for project in self.sub:
            yield project
    
    def build_main_project(self, ptree):
        return self.MAIN_PROJECT_CLASS(ptree, pm=self)
        
    def build_project(self, ptree):
        return self.PROJECT_CLASS(ptree, pm=self)

    pass