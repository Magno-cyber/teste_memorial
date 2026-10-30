/**
 * Aba Marcos: cartões com foto de época, ano, título e frase curta. Tocar abre o texto explicativo
 * (o cartão ganha a cor do espaço); tocar de novo ou em outro cartão fecha. Os quatro marcos do
 * tour cabem lado a lado; mais que isso rola para os lados, com encaixe.
 */
import { FotoEpoca } from '../componentes/FotoEpoca';
import { Icone } from '../componentes/Icone';
import type { Marco } from '../dados/tipos';

interface Props {
  marcos: Marco[];
  aberto: number | null;
  aoAlternar: (id: number | null) => void;
}

export function Marcos({ marcos, aberto, aoAlternar }: Props) {
  if (!marcos.length) {
    return <p className="tt-vazio entra">Este espaço ainda não tem marcos.</p>;
  }
  const rola = marcos.length > 4;
  return (
    <div className={['tt-marcos entra', rola && 'tt-marcos--rola'].filter(Boolean).join(' ')}>
      {marcos.map((m) => {
        const on = m.id === aberto;
        const longo = m.texto && m.texto !== m.descricao;
        return (
          <button
            key={m.id}
            type="button"
            className={['tt-mc tt-cartao', on && 'is-aberto'].filter(Boolean).join(' ')}
            aria-expanded={on}
            onClick={() => aoAlternar(on ? null : m.id)}
          >
            <span className="tt-mc__foto">
              <FotoEpoca src={m.foto} alt={m.titulo} icone={m.icone} semente={m.id} tamanhoIcone={52} />
              <span className="tt-mc__ano serif num">{m.ano}</span>
            </span>
            <span className="tt-mc__corpo">
              <span className="tt-mc__icone"><Icone nome={m.icone} tamanho={20} /></span>
              <span className="tt-mc__titulo serif">{m.titulo}</span>
              <span className="tt-mc__curto">{m.descricao}</span>
              {on && <span className="tt-mc__longo">{longo ? m.texto : m.descricao}</span>}
              <span className="tt-mc__dica">{on ? 'Toque para fechar' : 'Toque para ler mais'}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
