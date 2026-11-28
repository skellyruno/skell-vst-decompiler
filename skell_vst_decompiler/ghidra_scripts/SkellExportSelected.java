// Original targeted exporter for the optional Ghidra backend.
// @category Skell.Research
import ghidra.app.util.headless.HeadlessScript;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

public class SkellExportSelected extends HeadlessScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3 || args.length > 66) {
            throw new IllegalArgumentException("Expected output folder, SHA-256, and 1..64 RVAs");
        }
        if (analysisTimeoutOccurred()) throw new IllegalStateException("Initial analysis timed out");
        String sha = currentProgram.getExecutableSHA256();
        if (sha == null || !sha.equalsIgnoreCase(args[1])) {
            throw new IllegalArgumentException("Unexpected source fingerprint");
        }
        Path dir = Path.of(args[0]);
        if (!Files.isDirectory(dir)) throw new IllegalArgumentException("Missing private output directory");
        Address base = currentProgram.getImageBase();
        DecompInterface dc = new DecompInterface();
        DecompileOptions options = new DecompileOptions();
        options.setMaxPayloadMBytes(16);
        dc.setOptions(options);
        dc.toggleCCode(true);
        dc.toggleSyntaxTree(false);
        Map<Long,String> successes = new HashMap<>();
        try (BufferedWriter rows = Files.newBufferedWriter(dir.resolve("results.tsv"), StandardCharsets.UTF_8);
             BufferedWriter calls = Files.newBufferedWriter(dir.resolve("calls.tsv"), StandardCharsets.UTF_8)) {
            rows.write("SKELL_SHA256\t" + args[1] + "\n");
            if (!dc.openProgram(currentProgram)) throw new IllegalStateException("Decompiler open failed");
            for (int i = 2; i < args.length; i++) {
                monitor.checkCancelled();
                long rva = Long.decode(args[i]);
                Address target = base.add(rva);
                Function fn = currentProgram.getFunctionManager().getFunctionContaining(target);
                String prefix = "0x" + Long.toHexString(rva) + "\t";
                if (fn == null || fn.isExternal()) {
                    rows.write(prefix + "-\tno_function\t-\n");
                    continue;
                }
                long entry = fn.getEntryPoint().subtract(base);
                String entryText = "0x" + Long.toHexString(entry);
                String filename = successes.get(entry);
                if (filename == null) {
                    DecompileResults result = dc.decompileFunction(fn, 30, monitor);
                    if (result == null || !result.decompileCompleted() || result.getDecompiledFunction() == null) {
                        rows.write(prefix + entryText + "\tdecompile_failed\t-\n");
                        continue;
                    }
                    String code = result.getDecompiledFunction().getC();
                    if (code == null || code.isEmpty() || code.length() > 1000000) {
                        rows.write(prefix + entryText + "\tdecompile_failed\t-\n");
                        continue;
                    }
                    filename = "function_" + Long.toHexString(entry) + ".c.txt";
                    Files.writeString(dir.resolve(filename), code, StandardCharsets.UTF_8);
                    successes.put(entry, filename);
                    writeLinks(calls, entryText, "calls", fn.getCalledFunctions(monitor), base);
                    writeLinks(calls, entryText, "called_by", fn.getCallingFunctions(monitor), base);
                }
                rows.write(prefix + entryText + "\tok\t" + filename + "\n");
                rows.flush();
            }
            monitor.checkCancelled();
            calls.write("SKELL_COMPLETE\n");
            rows.write("SKELL_COMPLETE\n");
        } finally {
            dc.dispose();
        }
    }
    private void writeLinks(BufferedWriter writer, String entry, String kind,
                            Set<Function> functions, Address base) throws Exception {
        TreeSet<Long> addresses = new TreeSet<>();
        for (Function fn : functions) {
            monitor.checkCancelled();
            if (fn.isExternal() || !fn.getEntryPoint().getAddressSpace().equals(base.getAddressSpace())) continue;
            long rva = fn.getEntryPoint().subtract(base);
            if (rva >= 0 && rva <= 0xffffffffL) addresses.add(rva);
        }
        int count = 0;
        for (long rva : addresses) {
            if (count++ == 128) break;
            writer.write(entry + "\t" + kind + "\t0x" + Long.toHexString(rva) + "\n");
        }
    }
}
