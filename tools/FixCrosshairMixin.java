import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.AnnotationNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.IincInsnNode;
import org.objectweb.asm.tree.LocalVariableNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * 把 BridgingMod 的 CrosshairRenderingMixin 改成 26.4-snapshot-5 的签名。
 *
 * 26.3 的目标方法是 {@code Hud#extractCrosshair(GuiGraphicsExtractor, DeltaTracker)}，
 * snapshot-5 去掉了 DeltaTracker。handler 里那个参数<b>一次都没被读过</b>（局部变量从 4 开始用），
 * 所以删掉它只需把参数表、局部变量索引和栈帧里的槽位一起往前挪一格。
 */
public final class FixCrosshairMixin {

    private static final String OLD_PARAM = "Lnet/minecraft/client/DeltaTracker;";

    /** 要被去掉的形参在局部变量表里的槽位（0=this, 1=graphics, 2=deltaTracker, 3=callbackInfo）。 */
    private static final int DROP_SLOT = 2;

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("用法: FixCrosshairMixin <in.class> <out.class>");
            System.exit(1);
        }
        byte[] input = Files.readAllBytes(Path.of(args[0]));
        ClassNode cn = new ClassNode();
        new ClassReader(input).accept(cn, 0);

        boolean touched = false;
        for (MethodNode mn : cn.methods) {
            if (!mn.name.equals("renderPlacementAssistMarker")) {
                continue;
            }
            if (!mn.desc.contains(OLD_PARAM)) {
                System.out.println("描述符里已经没有 DeltaTracker，跳过");
                continue;
            }
            System.out.println("旧描述符: " + mn.desc);
            mn.desc = mn.desc.replace(OLD_PARAM, "");
            System.out.println("新描述符: " + mn.desc);

            // 局部变量槽位整体前移一格
            shiftSlots(mn);
            // 栈帧里也要删掉对应槽位，否则校验器会认为帧和 max_locals 对不上
            dropFromFrames(mn);
            // 局部变量调试表
            if (mn.localVariables != null) {
                mn.localVariables.removeIf(v -> v.index == DROP_SLOT);
                for (LocalVariableNode v : mn.localVariables) {
                    if (v.index > DROP_SLOT) {
                        v.index--;
                    }
                }
            }
            mn.maxLocals = Math.max(1, mn.maxLocals - 1);

            // @Inject(method = "…") 里的描述符
            fixAnnotations(mn);

            touched = true;
        }

        if (!touched) {
            System.err.println("没找到目标方法");
            System.exit(2);
        }

        ClassWriter cw = new ClassWriter(0);
        cn.accept(cw);
        Files.write(Path.of(args[1]), cw.toByteArray());
        System.out.println("已写出: " + args[1]);
    }

    /** 所有 VarInsn 的槽位号 >= DROP_SLOT+1 的往前挪一格。 */
    private static void shiftSlots(MethodNode mn) {
        int count = 0;
        for (AbstractInsnNode insn : mn.instructions) {
            if (insn instanceof VarInsnNode v) {
                // 槽位 DROP_SLOT 就是被删的参数，正常不该被引用；万一引用了，说明分析错了
                if (v.var == DROP_SLOT) {
                    throw new IllegalStateException("DeltaTracker 参数被使用了，不能简单删除");
                }
                if (v.var > DROP_SLOT) {
                    v.var--;
                    count++;
                }
            } else if (insn instanceof IincInsnNode i) {
                if (i.var == DROP_SLOT) {
                    throw new IllegalStateException("DeltaTracker 参数被使用了，不能简单删除");
                }
                if (i.var > DROP_SLOT) {
                    i.var--;
                    count++;
                }
            }
        }
        System.out.println("  重排了 " + count + " 处变量引用");
    }

    /** FrameNode.local 里每个槽位对应一个条目，删掉第 DROP_SLOT 个。 */
    private static void dropFromFrames(MethodNode mn) {
        int frames = 0;
        for (AbstractInsnNode insn : mn.instructions) {
            if (insn instanceof FrameNode f && f.local != null && f.local.size() > DROP_SLOT) {
                f.local.remove(DROP_SLOT);
                frames++;
            }
        }
        System.out.println("  调整了 " + frames + " 个栈帧");
    }

    private static void fixAnnotations(MethodNode mn) {
        if (mn.visibleAnnotations != null) {
            for (AnnotationNode an : mn.visibleAnnotations) {
                walk(an);
            }
        }
        if (mn.invisibleAnnotations != null) {
            for (AnnotationNode an : mn.invisibleAnnotations) {
                walk(an);
            }
        }
    }

    private static void walk(AnnotationNode an) {
        if (an == null || an.values == null) {
            return;
        }
        for (int i = 0; i < an.values.size(); i += 2) {
            Object key = an.values.get(i);
            Object val = an.values.get(i + 1);
            if ("method".equals(key)) {
                Object replaced = replaceIn(val);
                if (replaced != null) {
                    System.out.println("  注解 method: " + val + " → " + replaced);
                    an.values.set(i + 1, replaced);
                }
            }
            if (val instanceof AnnotationNode child) {
                walk(child);
            } else if (val instanceof List<?> list) {
                for (Object o : list) {
                    if (o instanceof AnnotationNode child) {
                        walk(child);
                    }
                }
            }
        }
    }

    private static Object replaceIn(Object val) {
        if (val instanceof String s) {
            return s.contains(OLD_PARAM) ? s.replace(OLD_PARAM, "") : null;
        }
        if (val instanceof List<?> list) {
            boolean hit = false;
            for (Object o : list) {
                if (o instanceof String s && s.contains(OLD_PARAM)) {
                    hit = true;
                    break;
                }
            }
            if (!hit) {
                return null;
            }
            @SuppressWarnings("unchecked")
            List<Object> mutable = (List<Object>) list;
            for (int i = 0; i < mutable.size(); i++) {
                if (mutable.get(i) instanceof String s && s.contains(OLD_PARAM)) {
                    mutable.set(i, s.replace(OLD_PARAM, ""));
                }
            }
            return mutable;
        }
        return null;
    }
}
