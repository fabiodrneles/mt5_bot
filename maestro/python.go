package main

import (
	"os"
	"path/filepath"
)

// pythonExe escolhe o interpretador dos workers (spec 002 FR-4):
//  1. MT5BOT_PYTHON, se definido;
//  2. o Python embutido da instalacao: <app>\python\python.exe, vizinho da
//     pasta do maestro.exe (<app>\maestro\maestro.exe);
//  3. o "python" do PATH (quem clonou o repositorio).
func pythonExe() string {
	exeDir := ""
	if exe, err := os.Executable(); err == nil {
		exeDir = filepath.Dir(exe)
	}
	return pythonExeFor(os.Getenv("MT5BOT_PYTHON"), exeDir)
}

func pythonExeFor(env, exeDir string) string {
	if env != "" {
		return env
	}
	if exeDir != "" {
		bundled := filepath.Join(exeDir, "..", "python", "python.exe")
		if info, err := os.Stat(bundled); err == nil && !info.IsDir() {
			return bundled
		}
	}
	return "python"
}
