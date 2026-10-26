import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.util.CheckClassAdapter;

import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** 检查改写后的 class：列出每个栈帧的局部变量槽位，并用 ASM 做结构校验。 */
public final class CheckFrames {
    public static void main(String[] args) throws Exception {
        byte[] data = Files.readAllBytes(Path.of(args[0]));
        ClassNode cn = new ClassNode();
        new ClassReader(data).accept(cn, 0);

        for (MethodNode mn : cn.methods) {
            if (!mn.name.equals("renderPlacementAssistMarker")) {
                continue;
            }
            System.out.println("方法: " + mn.desc);
            System.out.println("maxLocals = " + mn.maxLocals + ", maxStack = " + mn.maxStack);
            int i = 0;
            for (AbstractInsnNode insn : mn.instructions) {
                if (insn instanceof FrameNode f) {
                    List<String> slots = new ArrayList<>();
                    if (f.local != null) {
                        for (Object o : f.local) {
                            slots.add(String.valueOf(o));
                        }
                    }
                    System.out.println("  帧#" + (i++) + " type=" + f.type + " local(" + slots.size() + ")=" + slots);
                }
            }
        }

        System.out.println();
        System.out.println("=== CheckClassAdapter 结构校验 ===");
        CheckClassAdapter.verify(new ClassReader(data), false, new PrintWriter(System.out));
        System.out.println("(没有输出即通过)");
    }
}
