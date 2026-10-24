package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPythonExeForOrdemDeBusca(t *testing.T) {
	app := t.TempDir()
	maestroDir := filepath.Join(app, "maestro")
	bundled := filepath.Join(app, "python", "python.exe")
	os.MkdirAll(maestroDir, 0o755)
	os.MkdirAll(filepath.Dir(bundled), 0o755)

	if got := pythonExeFor("", maestroDir); got != "python" {
		t.Fatalf("sem Python embutido deveria usar o do PATH, veio %q", got)
	}
	os.WriteFile(bundled, []byte("x"), 0o755)
	if got := pythonExeFor("", maestroDir); filepath.Clean(got) != filepath.Clean(bundled) {
		t.Fatalf("com Python embutido deveria usa-lo, veio %q", got)
	}
	if got := pythonExeFor(`C:\custom\python.exe`, maestroDir); got != `C:\custom\python.exe` {
		t.Fatalf("MT5BOT_PYTHON deveria ter prioridade, veio %q", got)
	}
}
