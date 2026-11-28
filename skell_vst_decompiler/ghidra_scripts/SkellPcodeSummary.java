// Original aggregate P-code smoke exporter. No pseudocode, constants or operand data.
// @category Skell.Research
import ghidra.app.util.headless.HeadlessScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;

public class SkellPcodeSummary extends HeadlessScript {
    @Override
    public void run() throws Exception {
        String[] args=getScriptArgs();
        if (args.length<3 || args.length>18 || analysisTimeoutOccurred()) throw new IllegalArgumentException("Invalid bounded analysis");
        String sha=currentProgram.getExecutableSHA256();
        if (sha==null || !sha.equalsIgnoreCase(args[1])) throw new IllegalArgumentException("Source fingerprint mismatch");
        DecompInterface dc=new DecompInterface();
        DecompileOptions opts=new DecompileOptions();opts.setMaxPayloadMBytes(16);dc.setOptions(opts);
        dc.toggleCCode(false);dc.toggleSyntaxTree(true);
        StringBuilder out=new StringBuilder("SKELL_SHA256\t"+sha+"\n");
        try {
            if (!dc.openProgram(currentProgram)) throw new IllegalStateException("Decompiler open failed");
            for (int i=2;i<args.length;i++) {
                monitor.checkCancelled();
                long rva=Long.decode(args[i]);
                Function fn=currentProgram.getFunctionManager().getFunctionAt(currentProgram.getImageBase().add(rva));
                if (fn==null || fn.isExternal()) throw new IllegalStateException("No exact local entry");
                DecompileResults result=dc.decompileFunction(fn,30,monitor);
                if (result==null || !result.decompileCompleted()) throw new IllegalStateException("Decompile failed");
                HighFunction high=result.getHighFunction();
                if (high==null) throw new IllegalStateException("Missing high P-code");
                Map<String,Integer> counts=new TreeMap<>();int total=0,definedInputs=0;
                Iterator<PcodeOpAST> ops=high.getPcodeOps();
                while (ops.hasNext()) {
                    monitor.checkCancelled();PcodeOpAST op=ops.next();
                    if (++total>100000) throw new IllegalStateException("P-code bound exceeded");
                    counts.merge(op.getMnemonic(),1,Integer::sum);
                    for (int k=0;k<op.getNumInputs();k++) {
                        Varnode v=op.getInput(k);if (v!=null && v.getDef()!=null) definedInputs++;
                    }
                }
                if (total==0) throw new IllegalStateException("Empty P-code");
                out.append(args[i]).append('\t').append(total).append('\t').append(definedInputs);
                for (Map.Entry<String,Integer> e:counts.entrySet()) out.append('\t').append(e.getKey()).append('=').append(e.getValue());
                out.append('\n');
            }
            out.append("SKELL_COMPLETE\n");
            Files.writeString(Path.of(args[0]),out.toString());
        } finally {dc.dispose();}
    }
}
